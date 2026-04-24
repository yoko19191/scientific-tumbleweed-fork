import argparse
import base64
import os

import requests


def generate_image(
    prompt_file: str,
    output_file: str,
    size: str = "auto",
    quality: str = "high",
    n: int = 1,
) -> str:
    api_key = os.getenv("DMXAPI_API_KEY")
    if not api_key:
        raise RuntimeError("DMXAPI_API_KEY is not set")

    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read()

    response = requests.post(
        "https://www.dmxapi.cn/v1/images/generations",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json={
            "model": "gpt-image-2",
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
        },
        timeout=1000,
    )
    response.raise_for_status()
    data = response.json()

    if "data" not in data or not data["data"]:
        raise RuntimeError(f"Unexpected API response: {data}")

    saved = []
    for i, item in enumerate(data["data"], start=1):
        if item.get("b64_json"):
            image_bytes = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            image_bytes = requests.get(item["url"], timeout=120).content
        else:
            print(f"Warning: no image payload in response item {i}, skipping")
            continue

        if n == 1:
            path = output_file
        else:
            base, ext = os.path.splitext(output_file)
            path = f"{base}_{i}{ext}"

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(image_bytes)
        saved.append(path)

    if not saved:
        raise RuntimeError("No images were generated")

    return "Generated: " + ", ".join(saved)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images using DMXAPI gpt-image-2")
    parser.add_argument("--prompt-file", required=True, help="Path to prompt text file")
    parser.add_argument("--output-file", required=True, help="Output image path (.png)")
    parser.add_argument("--size", default="auto", choices=["auto", "1024x1024", "1536x1024", "1024x1536"], help="Image resolution")
    parser.add_argument("--quality", default="high", choices=["auto", "high", "medium", "low"], help="Image quality")
    parser.add_argument("--n", type=int, default=1, help="Number of images to generate (1-10)")

    args = parser.parse_args()

    try:
        print(generate_image(args.prompt_file, args.output_file, args.size, args.quality, args.n))
    except Exception as e:
        print(f"Error: {e}")
