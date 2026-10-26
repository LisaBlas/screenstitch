"""Build a common-coordinate comparison of the affine and two local trials."""
from pathlib import Path
import json
import cv2 as cv
import numpy as np

runs=[('poe2-v3','affine','Previous affine'),('poe2-local-v1','local-seams','Local: flexible'),('poe2-local-v2','local-seams','Local: limited stretch')]
output=Path('output/geometry/poe2-local-v2/comparison.jpg')
if output.exists():
    raise SystemExit('Comparison already exists; preserve it and choose a new output path.')
board=np.full((1000,2160,3),32,np.uint8)
for i,(folder,label,title) in enumerate(runs):
    root=Path('output/geometry')/folder
    im=cv.imread(str(root/f'{label}-preview.jpg'))
    s=min(720/im.shape[1],500/im.shape[0]);im=cv.resize(im,None,fx=s,fy=s)
    x=i*720+(720-im.shape[1])//2
    board[55:55+im.shape[0],x:x+im.shape[1]]=im
    cv.putText(board,title,(i*720+18,33),cv.FONT_HERSHEY_SIMPLEX,.85,(240,240,240),2)
    report=json.loads((root/'report.json').read_text());ox,oy=report['outputs'][label]['origin']
    rgba=cv.imread(str(root/f'{label}.png'),cv.IMREAD_UNCHANGED)
    crop=rgba[300-oy:950-oy,650-ox:1800-ox]
    crop=cv.resize(crop,(690,390),interpolation=cv.INTER_AREA)
    yy,xx=np.indices(crop.shape[:2]);bg=np.where((xx//12+yy//12)%2,42,64);alpha=crop[:,:,3:4]/255
    crop=(crop[:,:,:3]*alpha+bg[:,:,None]*(1-alpha)).astype(np.uint8)
    board[590:980,i*720+15:i*720+705]=crop
cv.putText(board,'Same scene region below. These are diagnostic outputs; none passes visual quality review.',(18,575),cv.FONT_HERSHEY_SIMPLEX,.75,(240,240,240),1)
if not cv.imwrite(str(output),board):
    raise RuntimeError('Could not save comparison')
