"""模型 2(Gemma-3-4b-it)的兼容层。对模型 1(Qwen3.5-9B)什么都不改:make_lm 对 Qwen 原样返回 ValueTuner 的 LM。
Gemma 和 Qwen 的三处不同:
  1. 检查点是多模态的 Gemma3ForConditionalGeneration,解码层在 model.model.language_model.layers;
  2. 回合结束符是 <end_of_turn>(id 106),分词器的 eos 是 <eos>(id 1),生成时两个都要当结束符;
  3. 对话模板没有独立的系统角色,系统提示被并进第一轮用户消息(这是 Gemma 官方模板的做法,论文里写明)。
最后一个 hidden state 过 lm_head 得到 logits;Gemma 3 没有 final_logit_softcapping(config 里是 None),概率读数可以直接 softmax。"""
import sys

sys.path.insert(0, "/root/autodl-tmp/vt")
import torch
from vt.model import LM


class GemmaLM(LM):
    @property
    def layers(self):
        m = self.model.model
        return m.language_model.layers if hasattr(m, "language_model") else m.layers

    @property
    def eos_ids(self):
        ids = {self.tok.eos_token_id, self.tok.convert_tokens_to_ids("<end_of_turn>")}
        g = self.model.generation_config.eos_token_id
        ids |= set(g if isinstance(g, list) else [g])
        return sorted(i for i in ids if i is not None and i != self.tok.unk_token_id)

    @torch.no_grad()
    def generate(self, prompts, max_new_tokens=300, temperature=0.0, **kw):
        enc = self.encode(prompts)
        gen = dict(max_new_tokens=max_new_tokens, pad_token_id=self.tok.pad_token_id, eos_token_id=self.eos_ids)
        if temperature and temperature > 0:   # 和 ValueTuner 的采样参数一致
            gen.update(do_sample=True, temperature=temperature, top_p=kw.pop("top_p", 0.8), top_k=kw.pop("top_k", 20))
        else:
            gen.update(do_sample=False, temperature=None, top_p=None, top_k=None)
        gen.update(kw)
        out = self.model.generate(**enc, **gen)
        return self.tok.batch_decode(out[:, enc.input_ids.shape[1]:], skip_special_tokens=True)


def make_lm(cfg):
    return GemmaLM(cfg) if "gemma" in cfg.model_path.lower() else LM(cfg)
