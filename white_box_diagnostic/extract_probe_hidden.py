"""Extract prompt-end hidden states for all 128 QDegradeBench prompts."""

from __future__ import annotations

import hashlib
import json
import platform
import random
from pathlib import Path

import numpy as np
import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "data" / "probe_prompts_128.jsonl"
OUTPUT_DIR = ROOT / "results" / "probe_qwen3_1_7b"
CACHE_DIR = ROOT / "models" / "hf"
MODEL_ID = "Qwen/Qwen3-1.7B"
SYSTEM_PROMPT = "你是一个乐于助人的人工智能助手。请回答用户的问题。"
SEED = 20260916


def read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def chat_tokens(tokenizer, prompt: str) -> torch.Tensor:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    kwargs = {
        "tokenize": True,
        "add_generation_prompt": True,
        "return_tensors": "pt",
    }
    try:
        encoded = tokenizer.apply_chat_template(
            messages, enable_thinking=False, **kwargs
        )
    except TypeError:
        encoded = tokenizer.apply_chat_template(messages, **kwargs)
    if isinstance(encoded, torch.Tensor):
        return encoded
    if hasattr(encoded, "input_ids"):
        return encoded.input_ids
    if isinstance(encoded, dict) and "input_ids" in encoded:
        return encoded["input_ids"]
    raise TypeError(f"Unsupported chat-template result: {type(encoded)!r}")


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cuda.matmul.allow_tf32 = False

    records = read_jsonl(INPUT_PATH)
    if len(records) != 128:
        raise RuntimeError(f"Expected 128 records, found {len(records)}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=CACHE_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        cache_dir=CACHE_DIR,
        dtype=torch.bfloat16,
        device_map={"": 0},
        low_cpu_mem_usage=True,
    ).eval()
    layer_count = int(model.config.num_hidden_layers) + 1
    hidden_size = int(model.config.hidden_size)
    hidden = np.empty((len(records), layer_count, hidden_size), dtype=np.float32)
    token_counts = np.empty(len(records), dtype=np.int32)

    for index, item in enumerate(records):
        input_ids = chat_tokens(tokenizer, str(item["prompt"])).to("cuda")
        attention_mask = torch.ones_like(input_ids)
        with torch.inference_mode():
            output = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
                use_cache=False,
                return_dict=True,
            )
        stacked = torch.stack(
            [layer[0, -1].float().cpu() for layer in output.hidden_states]
        ).numpy()
        if stacked.shape != (layer_count, hidden_size):
            raise RuntimeError(
                f"Unexpected shape for {item['sample_id']}: {stacked.shape}"
            )
        hidden[index] = stacked
        token_counts[index] = int(input_ids.shape[1])
        if (index + 1) % 16 == 0 or index == 0:
            print(
                f"Processed {index + 1}/128; sample={item['sample_id']}; "
                f"tokens={input_ids.shape[1]}; peak="
                f"{torch.cuda.max_memory_allocated()/1024**3:.2f} GiB"
            )
        del input_ids, attention_mask, output, stacked

    np.savez_compressed(
        OUTPUT_DIR / "prompt_end_hidden_128.npz",
        hidden=hidden,
        token_counts=token_counts,
        sample_ids=np.asarray([str(item["sample_id"]) for item in records]),
    )
    input_sha256 = hashlib.sha256(INPUT_PATH.read_bytes()).hexdigest()
    metadata = {
        "model_id": MODEL_ID,
        "model_commit": getattr(model.config, "_commit_hash", None),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "python": platform.python_version(),
        "cuda_runtime": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "dtype": "bfloat16",
        "seed": SEED,
        "system_prompt": SYSTEM_PROMPT,
        "hidden_state_unit": "last prompt token before generation",
        "record_count": len(records),
        "layer_count_including_embedding": layer_count,
        "hidden_size": hidden_size,
        "input_sha256": input_sha256,
        "min_input_tokens": int(token_counts.min()),
        "max_input_tokens": int(token_counts.max()),
    }
    (OUTPUT_DIR / "extraction_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"PASS: saved {hidden.shape} hidden states to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
