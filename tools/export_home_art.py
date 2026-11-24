"""Export original home artwork to bounded, alpha-preserving display assets."""
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]/'webgui_menu/home-assets'
for source in sorted(root.glob('*.png')):
    image=Image.open(source).convert('RGBA')
    image.thumbnail((512,512),Image.Resampling.LANCZOS)
    target=source.with_suffix('.webp')
    image.save(target,'WEBP',lossless=True,method=6)
    assert target.stat().st_size<300_000
    print(f'{target.name}: {target.stat().st_size:,} bytes')
assert sum(p.stat().st_size for p in root.glob('*.webp'))<1_000_000
