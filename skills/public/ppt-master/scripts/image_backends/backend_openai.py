#!/usr/bin/env python3
"""
OpenAI-compatible Image Generation Backend

Generates images through DMXAPI by default, while keeping OpenAI-compatible
configuration overrides for custom gateways.
Used by image_gen.py as a backend module.

Configuration keys:
  DMXAPI_API_KEY   (recommended) DMXAPI key
  OPENAI_API_KEY   (fallback) OpenAI/OpenAI-compatible key
  OPENAI_BASE_URL  (optional) Custom base URL or /images/generations endpoint
  OPENAI_MODEL     (optional) Model name (default: gpt-image-2)

Dependencies:
  pip install requests Pillow
"""

import base64
import os
import time
import threading
from urllib.parse import urljoin

import requests
from image_backends.backend_common import (
    MAX_RETRIES,
    is_rate_limit_error,
    normalize_image_size,
    resolve_output_path,
    retry_delay,
    save_image_bytes,
)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  Constants                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

# Aspect ratio -> OpenAI size mapping
# Covers common PPT/social media ratios
ASPECT_RATIO_TO_SIZE = {
    "1:1":  "1024x1024",
    "16:9": "1536x1024",
    "9:16": "1024x1536",
    "3:2":  "1536x1024",
    "2:3":  "1024x1536",
    "4:3":  "1536x1024",   # closest available
    "3:4":  "1024x1536",   # closest available
    "4:5":  "1024x1024",   # fallback to square
    "5:4":  "1024x1024",   # fallback to square
    "21:9": "1536x1024",   # closest wide format
}

VALID_ASPECT_RATIOS = list(ASPECT_RATIO_TO_SIZE.keys())

# image_size -> quality mapping
IMAGE_SIZE_TO_QUALITY = {
    "512px": "low",
    "1K":    "auto",
    "2K":    "high",
    "4K":    "high",
}

DEFAULT_BASE_URL = "https://www.dmxapi.cn/v1"
DEFAULT_MODEL = "gpt-image-2"


def _images_endpoint(base_url: str) -> str:
    """Resolve a base URL or explicit endpoint to /images/generations."""
    clean = (base_url or DEFAULT_BASE_URL).strip().rstrip("/")
    if clean.endswith("/images/generations"):
        return clean
    return urljoin(f"{clean}/", "images/generations")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  Image Generation                                               ║
# ╚══════════════════════════════════════════════════════════════════╝

def _generate_image(api_key: str, prompt: str, negative_prompt: str = None,
                    aspect_ratio: str = "1:1", image_size: str = "1K",
                    output_dir: str = None, filename: str = None,
                    model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE_URL) -> str:
    """
    Image generation via DMXAPI/OpenAI-compatible image generation endpoint.

    Maps aspect_ratio to a DMXAPI-compatible size parameter, and image_size to
    quality.

    Returns:
        Path of the saved image file

    Raises:
        RuntimeError: When generation fails
    """
    # Build prompt (OpenAI has no native negative_prompt, append to prompt)
    final_prompt = prompt
    if negative_prompt:
        final_prompt += f"\n\nAvoid the following: {negative_prompt}"

    # Map parameters
    size = ASPECT_RATIO_TO_SIZE.get(aspect_ratio, "1024x1024")
    quality = IMAGE_SIZE_TO_QUALITY.get(image_size, "auto")

    endpoint = _images_endpoint(base_url)
    mode_label = "DMXAPI" if endpoint.startswith("https://www.dmxapi.cn/") else f"Proxy: {endpoint}"
    print(f"[OpenAI-compatible - {mode_label}]")
    print(f"  Model:        {model}")
    print(f"  Prompt:       {final_prompt[:120]}{'...' if len(final_prompt) > 120 else ''}")
    print(f"  Size:         {size} (from aspect_ratio={aspect_ratio})")
    print(f"  Quality:      {quality} (from image_size={image_size})")
    print()

    start_time = time.time()
    print(f"  [..] Generating...", end="", flush=True)

    # Heartbeat thread
    heartbeat_stop = threading.Event()

    def _heartbeat():
        while not heartbeat_stop.is_set():
            heartbeat_stop.wait(5)
            if not heartbeat_stop.is_set():
                elapsed = time.time() - start_time
                print(f" {elapsed:.0f}s...", end="", flush=True)

    hb_thread = threading.Thread(target=_heartbeat, daemon=True)
    hb_thread.start()

    try:
        response = requests.post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "prompt": final_prompt,
                "n": 1,
                "size": size,
                "quality": quality,
            },
            timeout=180,
        )
        response.raise_for_status()
        data = response.json()
    finally:
        heartbeat_stop.set()
        hb_thread.join(timeout=1)

    elapsed = time.time() - start_time
    print(f"\n  [DONE] Image generated ({elapsed:.1f}s)")

    items = data.get("data") if isinstance(data, dict) else None
    if items:
        first = items[0]
        path = resolve_output_path(prompt, output_dir, filename, ".png")
        if first.get("b64_json"):
            image_data = base64.b64decode(first["b64_json"])
        elif first.get("url"):
            image_response = requests.get(first["url"], timeout=120)
            image_response.raise_for_status()
            image_data = image_response.content
        else:
            raise RuntimeError(f"No image payload in API response item: {first}")
        return save_image_bytes(image_data, path)

    raise RuntimeError(f"No image was generated. Unexpected API response: {data}")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  Public Entry Point                                             ║
# ╚══════════════════════════════════════════════════════════════════╝

def generate(prompt: str, negative_prompt: str = None,
             aspect_ratio: str = "1:1", image_size: str = "1K",
             output_dir: str = None, filename: str = None,
             model: str = None, max_retries: int = MAX_RETRIES) -> str:
    """
    OpenAI-compatible image generation with automatic retry.

    Reads credentials from the current process environment or the project-root `.env`:
      DMXAPI_API_KEY (preferred)
      OPENAI_API_KEY
      OPENAI_BASE_URL (optional; defaults to https://www.dmxapi.cn/v1)
      OPENAI_MODEL (optional override)

    Args:
        prompt: Positive prompt text
        negative_prompt: Negative prompt text (appended to prompt as "Avoid...")
        aspect_ratio: Aspect ratio, mapped to OpenAI size
        image_size: Image size, mapped to OpenAI quality
        output_dir: Output directory
        filename: Output filename (without extension)
        model: Model name (default: gpt-image-2)
        max_retries: Maximum number of retries

    Returns:
        Path of the saved image file
    """
    api_key = os.environ.get("DMXAPI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL

    if not api_key:
        raise ValueError(
            "No API key found. Set DMXAPI_API_KEY (recommended) or OPENAI_API_KEY "
            "in the current environment or the project-root .env."
        )

    if model is None:
        model = os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL

    image_size = normalize_image_size(image_size)

    if aspect_ratio not in ASPECT_RATIO_TO_SIZE:
        supported = list(ASPECT_RATIO_TO_SIZE.keys())
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}' for OpenAI backend. "
            f"Supported: {supported}"
        )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return _generate_image(api_key, prompt, negative_prompt,
                                   aspect_ratio, image_size, output_dir,
                                   filename, model, base_url)
        except Exception as e:
            last_error = e
            if attempt < max_retries and is_rate_limit_error(e):
                delay = retry_delay(attempt, rate_limited=True)
                print(f"\n  [WARN] Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                      f"Waiting {delay}s before retry...")
                time.sleep(delay)
            elif attempt < max_retries:
                delay = retry_delay(attempt, rate_limited=False)
                print(f"\n  [WARN] Error (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                      f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                break

    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
