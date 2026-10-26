"""Small PoE2 geometry experiment: source pixels, explicit masks, no synthesis.

Run from repository root. Requires experiments/requirements.txt.
Outputs are versioned by choosing a new, nonexistent --output directory.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2 as cv
import numpy as np


def mask_for(im, config):
    h, w = im.shape[:2]
    mask = np.full((h, w), 255, np.uint8)
    mask[[0, -1], :] = 0
    mask[:, [0, -1]] = 0
    for box in config['rectangles'].values():
        x0, y0, x1, y1 = box
        mask[int(y0*h):int(np.ceil(y1*h)), int(x0*w):int(np.ceil(x1*w))] = 0
    return mask


def project(points, matrix):
    p = np.column_stack((points, np.ones(len(points)))) @ matrix.T
    return p[:, :2] / p[:, 2:]


def intrinsic(im, focal):
    h, w = im.shape[:2]
    return np.array([[focal, 0, w/2], [0, focal, h/2], [0, 0, 1.]], dtype=np.float64)


def rotation_fit(a, b, ka, kb):
    def rays(p, k):
        r = np.column_stack((p, np.ones(len(p)))) @ np.linalg.inv(k).T
        return r / np.linalg.norm(r, axis=1)[:, None]
    ra, rb = rays(a, ka), rays(b, kb)
    u, _, vt = np.linalg.svd(rb.T @ ra)
    fix = np.diag([1., 1., np.linalg.det(u @ vt)])
    return u @ fix @ vt


def stats(errors):
    return {'median_px': float(np.median(errors)), 'p90_px': float(np.percentile(errors, 90))}


def write_image(path, im):
    if not cv.imwrite(str(path), im):
        raise RuntimeError(f'Could not write {path}')


def composite(layers, out, label):
    """Hard source selection keeps colours; distance from mask edges picks source."""
    x0 = min(x for (x, y), _, _ in layers)
    y0 = min(y for (x, y), _, _ in layers)
    x1 = max(x+im.shape[1] for (x, y), im, _ in layers)
    y1 = max(y+im.shape[0] for (x, y), im, _ in layers)
    w, h = x1-x0, y1-y0
    if w*h > 60_000_000:
        raise RuntimeError(f'Unreasonable canvas {w} x {h}')
    rgba = np.zeros((h, w, 4), np.uint8)
    score = np.zeros((h, w), np.float32)
    owner = np.zeros((h, w), np.uint8)
    for i, ((x, y), im, mask) in enumerate(layers):
        # Padding ensures image boundaries count as invalid for distance ranking.
        distance = cv.distanceTransform(np.pad(mask, 1), cv.DIST_L2, 3)[1:-1, 1:-1]
        xx, yy = x-x0, y-y0
        hh, ww = mask.shape
        s = score[yy:yy+hh, xx:xx+ww]
        take = (mask > 0) & (distance > s)
        dst = rgba[yy:yy+hh, xx:xx+ww]
        dst[take, :3] = im[take]
        dst[take, 3] = 255
        s[take] = distance[take]
        owner[yy:yy+hh, xx:xx+ww][take] = i+1
    write_image(out / f'{label}.png', rgba)
    write_image(out / f'{label}-source-map.png', owner)
    scale = min(1., 1800/w)
    preview = cv.resize(rgba, None, fx=scale, fy=scale, interpolation=cv.INTER_AREA)
    ph, pw = preview.shape[:2]
    yy, xx = np.indices((ph, pw))
    bg = np.where((xx//16 + yy//16) % 2, 42, 64).astype(np.uint8)
    alpha = preview[:, :, 3:4].astype(np.float32)/255
    preview = (preview[:, :, :3]*alpha + bg[:, :, None]*(1-alpha)).astype(np.uint8)
    write_image(out / f'{label}-preview.jpg', preview)
    return {'size': [w, h], 'covered_pixels': int(np.count_nonzero(owner)),
            'origin': [int(x0), int(y0)]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--indices', type=int, nargs='+', default=[3, 4, 5])
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if len(args.indices) < 2 or len(set(args.indices)) != len(args.indices):
        ap.error('Select at least two distinct source indices')
    if args.output.exists():
        ap.error('Output already exists; choose a new version')
    paths = sorted(Path('poe2').glob('*.png'))
    if any(i < 0 or i >= len(paths) for i in args.indices):
        ap.error('Source index out of range')
    paths = [paths[i] for i in args.indices]
    images = [cv.imread(str(p)) for p in paths]
    if any(im is None for im in images):
        raise RuntimeError('Unreadable input')
    config = json.loads(Path('experiments/masks.json').read_text())
    masks = [mask_for(im, config) for im in images]
    cv.setNumThreads(2)
    cv.setRNGSeed(42)
    sift = cv.SIFT_create(nfeatures=12000)
    features = [sift.detectAndCompute(cv.cvtColor(im, cv.COLOR_BGR2GRAY), m)
                for im, m in zip(images, masks)]
    matcher = cv.BFMatcher()
    pairs = []
    for i in range(1, len(images)):
        kp, desc = features[i]
        kp0, desc0 = features[0]
        if desc is None or desc0 is None:
            raise RuntimeError('Insufficient features after masking')
        matches = matcher.knnMatch(desc, desc0, k=2)
        good = [m for pair in matches if len(pair) == 2 for m, n in [pair]
                if m.distance < .7*n.distance]
        a = np.float32([kp[m.queryIdx].pt for m in good])
        b = np.float32([kp0[m.trainIdx].pt for m in good])
        if len(a) < 30:
            raise RuntimeError(f'Source {i}: only {len(a)} candidate matches')
        _, inliers = cv.findHomography(a, b, cv.RANSAC, 8.)
        if inliers is None or inliers.sum() < 30:
            raise RuntimeError(f'Source {i}: no reliable shared plane')
        keep = inliers.ravel().astype(bool)
        a, b = a[keep], b[keep]
        # Deterministic held-out subset. Robust prefilter used all points;
        # these metrics describe the dominant plane, not all scene depths.
        train = np.arange(len(a)) % 3 != 0
        delta = np.median(b[train]-a[train], axis=0)
        affine, _ = cv.estimateAffine2D(a[train], b[train], method=cv.RANSAC,
                                      ransacReprojThreshold=4)
        if affine is None:
            raise RuntimeError('Affine fit failed')
        pairs.append({'i': i, 'a': a, 'b': b, 'train': train,
                      'delta': delta, 'affine': np.vstack((affine, [0, 0, 1])),
                      'candidates': len(good)})
        print(f'Source {i}: {len(a)}/{len(good)} matches on dominant plane', flush=True)
    width = images[0].shape[1]
    focal_grid = width*np.geomspace(.5, 16, 36)
    focal_results = []
    for focal in focal_grid:
        errors = []
        for pair in pairs:
            i, a, b, t = (pair[k] for k in ('i', 'a', 'b', 'train'))
            ki, k0 = intrinsic(images[i], focal), intrinsic(images[0], focal)
            r = rotation_fit(a[t], b[t], ki, k0)
            pred = project(a[t], k0 @ r @ np.linalg.inv(ki))
            errors.extend(np.linalg.norm(pred-b[t], axis=1))
        focal_results.append(float(np.median(errors)))
    best_index = int(np.argmin(focal_results))
    best_focal = float(focal_grid[best_index])
    report = {'inputs': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                           'size': list(im.shape[1::-1])} for p, im in zip(paths, images)],
              'versions': {'opencv': cv.__version__, 'numpy': np.__version__},
              'masks': config, 'pairs': [], 'outputs': {},
              'method': 'SIFT ratio 0.7; homography RANSAC 8px prefilter; every third accepted match held out; focal chosen on training matches.',
              'limits': 'Metrics describe a dominant plane after prefilter, not all objects. Sphere assumes shared focal length, centred principal point and pure rotation. No calibration or depth recovery. Conservative masks may leave followers outside the central region.',
              'sphere_focal_px': best_focal, 'sphere_grid_boundary': best_index in (0, len(focal_grid)-1),
              'focal_search': [{'focal_px': float(f), 'training_median_px': e}
                               for f, e in zip(focal_grid, focal_results)]}
    args.output.mkdir(parents=True)
    for j, (im, mask) in enumerate(zip(images, masks)):
        write_image(args.output / f'mask-{j}.png', mask)
        preview = im.copy()
        preview[mask == 0] = (preview[mask == 0]*.25 + np.array([30, 0, 120])).clip(0,255)
        write_image(args.output / f'mask-{j}-preview.jpg', cv.resize(preview, (1024, 576)))
    flat_layers = [((0, 0), images[0], masks[0])]
    for pair in pairs:
        i, a, b, t = (pair[k] for k in ('i', 'a', 'b', 'train'))
        delta = np.rint(pair['delta']).astype(int)
        flat_layers.append((tuple(delta.tolist()), images[i], masks[i]))
        result = {'source_index': i, 'candidates': pair['candidates'], 'accepted': len(a),
                  'held_out': int((~t).sum()), 'translation': delta.tolist(),
                  'translation_error': stats(np.linalg.norm(a[~t]+delta-b[~t], axis=1)),
                  'affine_matrix': pair['affine'].tolist(),
                  'affine_error': stats(np.linalg.norm(project(a[~t], pair['affine'])-b[~t], axis=1))}
        report['pairs'].append(result)
    report['outputs']['flat'] = composite(flat_layers, args.output, 'flat')
    for label, focal in [('sphere', best_focal), ('sphere-focal-width', float(width))]:
        warper = cv.PyRotationWarper('spherical', focal)
        layers = []
        for i, (im, mask) in enumerate(zip(images, masks)):
            k = intrinsic(im, focal)
            r = np.eye(3)
            if i:
                pair = pairs[i-1]
                a, b, t = (pair[k] for k in ('a', 'b', 'train'))
                k0 = intrinsic(images[0], focal)
                r = rotation_fit(a[t], b[t], k, k0)
                err = np.linalg.norm(project(a[~t], k0 @ r @ np.linalg.inv(k))-b[~t], axis=1)
                report['pairs'][i-1][label+'_error'] = stats(err)
                report['pairs'][i-1][label+'_rotation'] = r.tolist()
            corner, warped = warper.warp(im, k.astype(np.float32), r.astype(np.float32),
                                         cv.INTER_NEAREST, cv.BORDER_CONSTANT)
            mask_corner, wm = warper.warp(mask, k.astype(np.float32), r.astype(np.float32),
                                          cv.INTER_NEAREST, cv.BORDER_CONSTANT)
            assert corner == mask_corner and warped.shape[:2] == wm.shape
            layers.append((corner, warped, wm))
        report['outputs'][label] = composite(layers, args.output, label)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'pairs': report['pairs'], 'focal': best_focal, 'outputs': report['outputs']}, indent=2))


if __name__ == '__main__':
    main()
