"""Fine-tune Whisper on Indian-accented English (Svarah), resumable.

Full fine-tune of openai/whisper-base.en - the model the app already runs -
on the speaker-disjoint train split from tools/train/data.py. Plain PyTorch
loop rather than HF Trainer so checkpointing is explicit:

  checkpoints/<run>/last/      model + optimizer + scheduler + scaler + step
                               (resume from here, on any machine)
  checkpoints/<run>/best/      HF-format weights with the lowest dev WER
  checkpoints/<run>/log.csv    step, train loss, dev WER

checkpoints/ is gitignored (hundreds of MB). The best model is exported for
the app with tools/train/export.py; that small int8 copy is what gets
committed.

Usage:
  python -m tools.train.train --run base_en_svarah
  python -m tools.train.train --run base_en_svarah --resume     # continue
"""
import argparse
import csv
import math
import os
import random
import sys
import time

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

from tools.train import data  # noqa: E402
from tools.train.metrics import wer_corpus  # noqa: E402

BASE_MODEL = "openai/whisper-base.en"


class SvarahDataset(Dataset):
    def __init__(self, rows, processor):
        self.rows, self.processor = rows, processor

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        audio = data.load_audio(r)
        feats = self.processor.feature_extractor(
            audio, sampling_rate=16000, return_tensors="np").input_features[0]
        labels = self.processor.tokenizer(r["text"]).input_ids
        return {"input_features": feats, "labels": labels}


def collate(batch, processor, decoder_start_id):
    feats = torch.tensor(np.stack([b["input_features"] for b in batch]))
    lab = processor.tokenizer.pad({"input_ids": [b["labels"] for b in batch]}, return_tensors="pt")
    labels = lab["input_ids"].masked_fill(lab["attention_mask"].ne(1), -100)
    # The model prepends decoder_start itself when shifting labels right.
    if (labels[:, 0] == decoder_start_id).all():
        labels = labels[:, 1:]
    return {"input_features": feats, "labels": labels}


@torch.no_grad()
def evaluate(model, processor, rows, device, batch_size=16, limit=None):
    model.eval()
    rows = rows[:limit] if limit else rows
    refs, hyps = [], []
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        feats = processor.feature_extractor(
            [data.load_audio(r) for r in chunk], sampling_rate=16000,
            return_tensors="pt").input_features.to(device, torch.float16)
        with torch.autocast("cuda", dtype=torch.float16):
            out = model.generate(feats, max_new_tokens=128, num_beams=1)
        hyps += processor.batch_decode(out, skip_special_tokens=True)
        refs += [r["text"] for r in chunk]
    model.train()
    return wer_corpus(refs, hyps)


def save_weights(path, model, processor):
    model.save_pretrained(path)
    processor.save_pretrained(path)
    # transformers 5 folds this into processor_config.json, but CTranslate2's
    # converter (tools/train/export.py) still expects the standalone file.
    processor.feature_extractor.save_pretrained(path)


def save_state(path, model, opt, sched, scaler, step, epoch, best_wer):
    os.makedirs(path, exist_ok=True)
    tmp = os.path.join(path, "state.pt.tmp")
    torch.save({
        "model": model.state_dict(), "optimizer": opt.state_dict(),
        "scheduler": sched.state_dict(), "scaler": scaler.state_dict(),
        "step": step, "epoch": epoch, "best_wer": best_wer,
        "rng": {"python": random.getstate(), "numpy": np.random.get_state(),
                "torch": torch.get_rng_state(), "cuda": torch.cuda.get_rng_state_all()},
    }, tmp)
    os.replace(tmp, os.path.join(path, "state.pt"))  # atomic: a crash never corrupts it


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="base_en_svarah")
    ap.add_argument("--base", default=BASE_MODEL)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--eval-every", type=int, default=200)
    ap.add_argument("--save-every", type=int, default=200)
    ap.add_argument("--dev-limit", type=int, default=400, help="dev utterances per eval")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    os.chdir(_REPO_ROOT)

    from transformers import WhisperForConditionalGeneration, WhisperProcessor, get_linear_schedule_with_warmup

    if not torch.cuda.is_available():
        sys.exit("CUDA GPU not available - training needs the NVIDIA GPU (plugged in).")
    device = "cuda"
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)

    run_dir = os.path.join("checkpoints", args.run)
    last_dir, best_dir = os.path.join(run_dir, "last"), os.path.join(run_dir, "best")
    log_path = os.path.join(run_dir, "log.csv")

    processor = WhisperProcessor.from_pretrained(args.base)
    model = WhisperForConditionalGeneration.from_pretrained(args.base).to(device)
    model.config.forced_decoder_ids = None
    model.generation_config.forced_decoder_ids = None
    decoder_start_id = model.config.decoder_start_token_id

    splits = data.load_splits()
    train_rows, dev_rows = splits["train"], splits["dev"]
    print(f"train {len(train_rows)} utts / dev {len(dev_rows)} utts")

    dataset = SvarahDataset(train_rows, processor)
    steps_per_epoch = math.ceil(len(dataset) / args.batch_size)
    total_steps = args.epochs * steps_per_epoch

    def epoch_loader(epoch, skip_batches):
        # Order is a pure function of (seed, epoch), so a resumed run sees
        # exactly the batches the interrupted run had not reached yet - and
        # never decodes the audio of the ones it skips.
        order = torch.randperm(len(dataset), generator=torch.Generator().manual_seed(args.seed + epoch))
        remaining = order[skip_batches * args.batch_size:].tolist()
        return DataLoader(torch.utils.data.Subset(dataset, remaining), batch_size=args.batch_size,
                          shuffle=False, num_workers=0,
                          collate_fn=lambda b: collate(b, processor, decoder_start_id))

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, args.warmup, total_steps)
    scaler = torch.amp.GradScaler("cuda")
    step, start_epoch, best_wer = 0, 0, math.inf

    if args.resume:
        # Load to CPU: RNG states must stay CPU ByteTensors; model and
        # optimizer state are moved to the GPU by load_state_dict.
        st = torch.load(os.path.join(last_dir, "state.pt"), map_location="cpu", weights_only=False)
        model.load_state_dict(st["model"]); opt.load_state_dict(st["optimizer"])
        sched.load_state_dict(st["scheduler"]); scaler.load_state_dict(st["scaler"])
        step, start_epoch, best_wer = st["step"], st["epoch"], st["best_wer"]
        random.setstate(st["rng"]["python"]); np.random.set_state(st["rng"]["numpy"])
        torch.set_rng_state(st["rng"]["torch"]); torch.cuda.set_rng_state_all(st["rng"]["cuda"])
        print(f"resumed at step {step} (epoch {start_epoch}), best dev WER {best_wer:.4f}")
    else:
        os.makedirs(run_dir, exist_ok=True)
        with open(log_path, "w", newline="") as f:
            csv.writer(f).writerow(["step", "epoch", "train_loss", "dev_wer", "lr", "elapsed_s"])
        base_wer = evaluate(model, processor, dev_rows, device, limit=args.dev_limit)
        print(f"step 0 (no training): dev WER {base_wer:.4f}")
        with open(log_path, "a", newline="") as f:
            csv.writer(f).writerow([0, 0, "", round(base_wer, 4), args.lr, 0])
        best_wer = base_wer

    model.train()
    t0, running = time.time(), []
    start_epoch = step // steps_per_epoch
    for epoch in range(start_epoch, args.epochs):
        skip = step - epoch * steps_per_epoch  # batches already done this epoch (on resume)
        for batch in epoch_loader(epoch, skip):
            feats = batch["input_features"].to(device)
            labels = batch["labels"].to(device)
            with torch.autocast("cuda", dtype=torch.float16):
                loss = model(input_features=feats, labels=labels).loss
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True); sched.step()
            step += 1
            running.append(loss.item())

            if step % 25 == 0:
                print(f"step {step}/{total_steps}  loss {np.mean(running[-25:]):.4f}  "
                      f"{(time.time() - t0) / 60:.1f} min", flush=True)

            dev_wer = ""
            if step % args.eval_every == 0 or step == total_steps:
                dev_wer = evaluate(model, processor, dev_rows, device, limit=args.dev_limit)
                print(f"step {step}: dev WER {dev_wer:.4f} (best {best_wer:.4f})", flush=True)
                if dev_wer < best_wer:
                    best_wer = dev_wer
                    save_weights(best_dir, model, processor)
                    print(f"  new best -> {best_dir}", flush=True)
            if step % args.save_every == 0 or step == total_steps or dev_wer != "":
                save_state(last_dir, model, opt, sched, scaler, step, epoch, best_wer)
                with open(log_path, "a", newline="") as f:
                    csv.writer(f).writerow([step, epoch, round(float(np.mean(running[-50:])), 4),
                                            "" if dev_wer == "" else round(dev_wer, 4),
                                            sched.get_last_lr()[0], int(time.time() - t0)])

    final_dir = os.path.join(run_dir, "final")
    save_weights(final_dir, model, processor)
    print(f"done. last-step weights -> {final_dir}")
    if os.path.isdir(best_dir):
        print(f"best dev WER {best_wer:.4f} -> {best_dir}  (export this one)")
    else:
        print("note: training never beat the untrained model on dev - no best/ saved; "
              "keep using the stock model")


if __name__ == "__main__":
    main()
