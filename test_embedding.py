"""Smoke test: run an embedding model through vLLM on CPU."""
import numpy as np
from vllm import LLM

MODEL = "intfloat/e5-small-v2"

prompts = [
    "query: how do I install vllm?",
    "passage: vLLM is a fast and easy-to-use library for LLM inference.",
    "passage: The capital of France is Paris.",
]


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def main():
    llm = LLM(model=MODEL, runner="pooling", enforce_eager=True)
    outputs = llm.embed(prompts)

    embs = [np.array(o.outputs.embedding, dtype=np.float32) for o in outputs]
    print(f"\nmodel: {MODEL}")
    print(f"num prompts: {len(embs)}")
    print(f"embedding dim: {embs[0].shape[0]}")

    print("\ncosine similarity vs prompt[0] (the vllm query):")
    for i, e in enumerate(embs):
        print(f"  prompt[{i}]: {cos(embs[0], e):+.4f}  | {prompts[i][:55]}")


if __name__ == "__main__":
    main()
