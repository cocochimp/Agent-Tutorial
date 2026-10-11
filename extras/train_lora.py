"""LoRA/SFT教学：assistant-only loss，训练/验证分开，保存adapter。
--smoke 用随机微型GPT2跑CPU更新，不下载基础权重，不代表中文能力。
--model 指向实际CAUSAL_LM基础模型；--data 接收messages格式JSONL。
"""
import argparse
import json
from pathlib import Path
import torch
from peft import LoraConfig, TaskType, get_peft_model, PeftModel
from transformers import AutoTokenizer, AutoModelForCausalLM, GPT2Config, GPT2LMHeadModel, PreTrainedTokenizerFast

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--smoke',action='store_true')
    p.add_argument('--model')
    p.add_argument('--data',default=str(ROOT/'extras'/'sft_examples.jsonl'))
    p.add_argument('--steps',type=int,default=12)
    p.add_argument('--output',default=str(ROOT/'output'/'lora_adapter'))
    args=p.parse_args()
    torch.manual_seed(42);torch.set_num_threads(2)
    records=[json.loads(line) for line in Path(args.data).read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    if len(records)<4: raise ValueError('至少需要4条样例，用于训练/验证拆分。')
    if args.smoke:
        from tokenizers import Tokenizer, models, pre_tokenizers
        tokens=sorted(set(''.join(m['content'] for r in records for m in r['messages'])+'systemuserassistant:\n'))
        vocab={t:i for i,t in enumerate(['[PAD]','[UNK]','[EOS]']+tokens)}
        core=Tokenizer(models.WordLevel(vocab,unk_token='[UNK]'))
        core.pre_tokenizer=pre_tokenizers.Split('',behavior='isolated')
        tok=PreTrainedTokenizerFast(tokenizer_object=core,pad_token='[PAD]',unk_token='[UNK]',eos_token='[EOS]')
        base=GPT2LMHeadModel(GPT2Config(vocab_size=len(tok),n_embd=32,n_layer=2,n_head=2,n_positions=512,pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id))
        target=['c_attn']
    else:
        if not args.model: p.error('使用--smoke或--model 指定基础模型')
        tok=AutoTokenizer.from_pretrained(args.model)
        if tok.pad_token_id is None: tok.pad_token=tok.eos_token
        base=AutoModelForCausalLM.from_pretrained(args.model,torch_dtype=torch.float32)
        target='all-linear'
    adapter=get_peft_model(base,LoraConfig(task_type=TaskType.CAUSAL_LM,r=4,lora_alpha=8,lora_dropout=0,target_modules=target))
    device='cuda' if torch.cuda.is_available() and not args.smoke else 'cpu'
    adapter.to(device)
    def batch(record):
        messages=record['messages']
        assert messages[-1]['role']=='assistant'
        if tok.chat_template:
            prefix=tok.apply_chat_template(messages[:-1],tokenize=False,add_generation_prompt=True)
            full=tok.apply_chat_template(messages,tokenize=False)
        else:
            prefix=''.join(m['role']+':'+m['content']+'\n' for m in messages[:-1])+'assistant:'
            full=prefix+messages[-1]['content']+tok.eos_token
        ids=tok(full,return_tensors='pt',truncation=True,max_length=512,add_special_tokens=False).to(device)
        length=len(tok(prefix,add_special_tokens=False)['input_ids'])
        labels=ids['input_ids'].clone();labels[:,:length]=-100
        if not (labels!=-100).any(): raise ValueError('答案被长度限制截断；缩短样例。')
        return {**ids,'labels':labels}
    train,valid=records[:-1],records[-1:]
    trainable={n:p.detach().clone() for n,p in adapter.named_parameters() if p.requires_grad}
    optim=torch.optim.AdamW([p for p in adapter.parameters() if p.requires_grad],lr=3e-3 if args.smoke else 2e-4)
    trainable_count=sum(p.numel() for p in adapter.parameters() if p.requires_grad)
    adapter.train();losses=[]
    for step in range(args.steps):
        optim.zero_grad();loss=adapter(**batch(train[step%len(train)])).loss
        loss.backward();optim.step();losses.append(float(loss.detach()))
    changed=any(not torch.equal(trainable[n],p.detach()) for n,p in adapter.named_parameters() if n in trainable)
    assert changed and all(torch.isfinite(torch.tensor(losses)))
    adapter.eval()
    with torch.no_grad(): validation=float(adapter(**batch(valid[0])).loss)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    adapter.save_pretrained(out);tok.save_pretrained(out)
    if args.smoke:
        # 随机基础模型一并保存，确保adapter重载有相同基座。
        base_dir=out/'smoke_base'
        base_model=adapter.unload();base_model.save_pretrained(base_dir)
        loaded=PeftModel.from_pretrained(GPT2LMHeadModel.from_pretrained(base_dir),out)
        assert loaded is not None
    summary={'scope':'随机微型模型管线验证，非领域效果评测' if args.smoke else '领域SFT训练，需另做独立业务评测','train_records':len(train),'validation_records':len(valid),'steps':args.steps,'trainable_parameters':trainable_count,'weights_changed':changed,'losses':losses,'validation_loss':validation,'device':device}
    (out/'training_result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
