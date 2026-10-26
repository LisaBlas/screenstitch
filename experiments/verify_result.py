"""Validate saved output structure and every copied pixel in a flat composite."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2 as cv
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('result', type=Path)
    args = ap.parse_args()
    report = json.loads((args.result/'report.json').read_text())
    for source in report['inputs']:
        assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest() == source['sha256'], source['path']
    for label, entry in report['outputs'].items():
        rgba = cv.imread(str(args.result/f'{label}.png'), cv.IMREAD_UNCHANGED)
        owner = cv.imread(str(args.result/f'{label}-source-map.png'), cv.IMREAD_UNCHANGED)
        assert rgba is not None and rgba.shape[2] == 4, label
        assert list(rgba.shape[1::-1]) == entry['size'], label
        assert owner.shape == rgba.shape[:2], label
        assert set(np.unique(rgba[:, :, 3])) <= {0, 255}, label
        assert np.array_equal(rgba[:, :, 3] > 0, owner > 0), label
        assert owner.max() <= len(report['inputs']), label
        assert np.count_nonzero(owner) == entry['covered_pixels'], label
    rgba = cv.imread(str(args.result/'flat.png'), cv.IMREAD_UNCHANGED)
    owner = cv.imread(str(args.result/'flat-source-map.png'), cv.IMREAD_UNCHANGED)
    origin = np.array(report['outputs']['flat']['origin'])
    offsets = [[0, 0]] + [pair['translation'] for pair in report['pairs']]
    checked = 0
    for i, (source, offset) in enumerate(zip(report['inputs'], offsets)):
        im = cv.imread(source['path'])
        mask = cv.imread(str(args.result/f'mask-{i}.png'), cv.IMREAD_GRAYSCALE)
        y, x = np.where(owner == i+1)
        sx, sy = x+origin[0]-offset[0], y+origin[1]-offset[1]
        assert (sx >= 0).all() and (sx < im.shape[1]).all()
        assert (sy >= 0).all() and (sy < im.shape[0]).all()
        assert (mask[sy, sx] > 0).all(), 'Masked pixels leaked'
        assert np.array_equal(rgba[y, x, :3], im[sy, sx]), 'Source colour changed'
        checked += len(x)
    result = {'status': 'passed', 'flat_pixels_verified_exact': checked,
              'outputs_checked': list(report['outputs']),
              'scope': 'Input hashes, output sizes, alpha/owner/coverage consistency and exact flat-source pixels; not scene geometry or mask completeness.'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
