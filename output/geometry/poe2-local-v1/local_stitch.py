"""Masked, regularized local mesh registration and source-selecting seams.
Run from repo root; uses only the already approved OpenCV and NumPy packages.
"""
import argparse
import hashlib
import json
from pathlib import Path
import cv2 as cv
import numpy as np
from compare_projections import mask_for, composite, write_image, stats


def basis(points, width, height, nx=20, ny=12):
    q = points / [width-1, height-1] * [nx-1, ny-1]
    x, y = np.clip(q[:, 0], 0, nx-1-1e-6), np.clip(q[:, 1], 0, ny-1-1e-6)
    ix, iy = x.astype(int), y.astype(int)
    fx, fy = x-ix, y-iy
    a = np.zeros((len(q), nx*ny))
    for dx, dy, weight in [(0,0,(1-fx)*(1-fy)),(1,0,fx*(1-fy)),(0,1,(1-fx)*fy),(1,1,fx*fy)]:
        a[np.arange(len(q)), (iy+dy)*nx+ix+dx] = weight
    return a


def fit_mesh(q, residual, shape, nx=20, ny=12):
    height, width = shape
    a = basis(q, width, height, nx, ny)
    regularizers = []
    # Penalise curvature; preserve the translation baseline far from evidence.
    for y in range(ny):
        for x in range(nx):
            i=y*nx+x
            for neighbors in ([i-1,i,i+1] if 0<x<nx-1 else [],
                              [i-nx,i,i+nx] if 0<y<ny-1 else []):
                if neighbors:
                    row=np.zeros(nx*ny);row[neighbors]=[1,-2,1];regularizers.append(row)
    reg=np.array(regularizers)
    penalty=.25*reg.T@reg + .015*np.eye(nx*ny)
    weights=np.ones(len(a))
    for _ in range(4):
        nodes=np.linalg.solve(a.T@(a*weights[:,None])+penalty,
                              a.T@(residual*weights[:,None]))
        err=np.linalg.norm(a@nodes-residual,axis=1)
        weights=np.minimum(1., 12/np.maximum(err,1e-6))
    return nodes.reshape(ny,nx,2)


def find_anchors(fs, i):
    k,d=fs[i];k0,d0=fs[0]
    matcher=cv.FlannBasedMatcher(dict(algorithm=1,trees=5),dict(checks=100))
    forward=matcher.knnMatch(d,d0,k=2);backward=matcher.knnMatch(d0,d,k=2)
    back={m.queryIdx:m.trainIdx for m,n in backward if m.distance<.75*n.distance}
    good=[m for m,n in forward if m.distance<.75*n.distance and back.get(m.trainIdx)==m.queryIdx]
    a=np.float32([k[m.queryIdx].pt for m in good]);b=np.float32([k0[m.trainIdx].pt for m in good])
    if len(a)<30:raise RuntimeError('Not enough mutual matches')
    delta=np.median(b-a,axis=0)
    keep=np.linalg.norm((b-a)-delta,axis=1)<450
    a,b=a[keep],b[keep]
    remain=np.arange(len(a));accepted=[];counts=[]
    for _ in range(8):
        if len(remain)<12:break
        _,ins=cv.findHomography(a[remain],b[remain],cv.RANSAC,5,maxIters=5000)
        if ins is None or ins.sum()<12:break
        chosen=remain[ins.ravel()>0];accepted.extend(chosen.tolist());counts.append(len(chosen));remain=remain[ins.ravel()==0]
    if len(accepted)<30:raise RuntimeError('Not enough robust local matches')
    return a[accepted],b[accepted],counts,len(good)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--reference',type=Path,default=Path('output/geometry/poe2-v3/report.json'))
    args=ap.parse_args()
    if args.output.exists():ap.error('Output already exists; choose a new version')
    cv.setNumThreads(2);cv.setRNGSeed(42)
    base=json.loads(args.reference.read_text())
    images=[cv.imread(s['path']) for s in base['inputs']]
    if any(im is None for im in images):raise RuntimeError('Missing source')
    for s in base['inputs']:
        if hashlib.sha256(Path(s['path']).read_bytes()).hexdigest()!=s['sha256']:raise RuntimeError('Source changed')
    masks=[mask_for(im,base['masks']) for im in images]
    sift=cv.SIFT_create(contrastThreshold=.025)
    fs=[sift.detectAndCompute(cv.cvtColor(im,cv.COLOR_BGR2GRAY),m) for im,m in zip(images,masks)]
    args.output.mkdir(parents=True)
    report={'inputs':base['inputs'],'masks':base['masks'],'versions':base['versions'],
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'parameters':{'grid':[20,12],'curvature_penalty':.25,'zero_displacement_penalty':.015,
                          'huber_px':12,'padding':160,'seam_scale':.35},
            'limits':'Multiple RANSAC clusters are geometric hypotheses, not semantic/depth labels. Prefilter uses all matches before holdout. Peripheral figures are not fully masked.',
            'pairs':[],'outputs':{}}
    layers=[((0,0),images[0],masks[0])]
    maps=[]
    pad=160
    for i in range(1,len(images)):
        a,b,counts,candidates=find_anchors(fs,i)
        delta=np.array(base['pairs'][i-1]['translation'])
        h,w=images[i].shape[:2];shape=(h+2*pad,w+2*pad)
        q=b-delta+pad;residual=a-(b-delta)
        keep=((q>0)&(q<[shape[1]-1,shape[0]-1])).all(axis=1)
        a,b,q,residual=a[keep],b[keep],q[keep],residual[keep]
        train=np.arange(len(a))%3!=0
        grid=fit_mesh(q[train],residual[train],shape)
        predicted=b[~train]-delta+basis(q[~train],shape[1],shape[0])@grid.reshape(-1,2)
        error=stats(np.linalg.norm(predicted-a[~train],axis=1))
        # Rendering uses the same training-only fit reported above.
        yy,xx=np.indices(shape,dtype=np.float32)
        # remap the grid by node coordinates; cv.resize has different pixel centres.
        gx=xx/(shape[1]-1)*(grid.shape[1]-1);gy=yy/(shape[0]-1)*(grid.shape[0]-1)
        flow=cv.remap(grid.astype(np.float32),gx,gy,cv.INTER_LINEAR)
        mapx=xx-pad+flow[:,:,0];mapy=yy-pad+flow[:,:,1]
        dyx,dxx=np.gradient(mapx[::8,::8],8);dyy,dxy=np.gradient(mapy[::8,::8],8)
        determinant=dxx*dyy-dxy*dyx
        if determinant.min()<=.1:raise RuntimeError('Mesh folds or nearly collapses; reject output')
        warped=cv.remap(images[i],mapx,mapy,cv.INTER_NEAREST,borderMode=cv.BORDER_CONSTANT)
        wm=cv.remap(masks[i],mapx,mapy,cv.INTER_NEAREST,borderMode=cv.BORDER_CONSTANT)
        corner=tuple((delta-pad).tolist());layers.append((corner,warped,wm));maps.append((mapx,mapy))
        np.savez_compressed(args.output/f'mesh-{i}.npz',grid=grid,a=a,b=b,train=train,corner=corner,shape=shape)
        debug=images[i].copy()
        for x,y in a:cv.circle(debug,(round(float(x)),round(float(y))),8,(0,0,255),2)
        write_image(args.output/f'anchors-{i}.jpg',cv.resize(debug,(1024,576)))
        report['pairs'].append({'source_index':i,'mutual_matches':candidates,'cluster_counts':counts,
                                'accepted':len(a),'held_out':int((~train).sum()),'mesh_error':error,
                                'minimum_sampled_jacobian':float(determinant.min()),
                                'maximum_displacement_px':float(np.linalg.norm(flow,axis=2).max())})
        print(report['pairs'][-1],flush=True)
    report['outputs']['local-distance']=composite(layers,args.output,'local-distance')
    # Select seams at reduced resolution, then enforce source validity at full size.
    scale=.35
    small=[cv.resize(im,None,fx=scale,fy=scale).astype(np.float32) for _,im,_ in layers]
    smasks=[cv.UMat(cv.resize(m,(im.shape[1],im.shape[0]),interpolation=cv.INTER_NEAREST))
            for (_,_,m),im in zip(layers,small)]
    corners=[(round(x*scale),round(y*scale)) for (x,y),_,_ in layers]
    seam=cv.detail_GraphCutSeamFinder('COST_COLOR_GRAD')
    seam.find(small,corners,smasks)
    seamlayers=[]
    # Keep the red-headdress NPC intact from the unchanged reference screenshot.
    protected=[880,420,1090,810]
    for i,((x,y),im,m),sm in zip(range(len(layers)),layers,smasks):
        selected=cv.resize(sm.get(),(m.shape[1],m.shape[0]),interpolation=cv.INTER_NEAREST)
        selected=cv.bitwise_and(selected,m)
        x0,y0,x1,y1=protected
        lx0,ly0=max(0,x0-x),max(0,y0-y);lx1,ly1=min(m.shape[1],x1-x),min(m.shape[0],y1-y)
        if lx0<lx1 and ly0<ly1:
            region=selected[ly0:ly1,lx0:lx1]
            valid=masks[0][ly0+y:ly1+y,lx0+x:lx1+x]>0
            if i==0:region[valid]=255
            else:region[valid]=0
        seamlayers.append(((x,y),im,selected))
    report['outputs']['local-seams']=composite(seamlayers,args.output,'local-seams')
    # Restore coverage that seam-mask down/up-sampling can lose at image edges.
    final=cv.imread(str(args.output/'local-seams.png'),cv.IMREAD_UNCHANGED)
    fallback=cv.imread(str(args.output/'local-distance.png'),cv.IMREAD_UNCHANGED)
    owner=cv.imread(str(args.output/'local-seams-source-map.png'),0)
    fallback_owner=cv.imread(str(args.output/'local-distance-source-map.png'),0)
    missing=(final[:,:,3]==0)&(fallback[:,:,3]>0)
    final[missing]=fallback[missing];owner[missing]=fallback_owner[missing]
    write_image(args.output/'local-seams.png',final);write_image(args.output/'local-seams-source-map.png',owner)
    report['outputs']['local-seams']['covered_pixels']=int(np.count_nonzero(owner))
    report['seam_fallback_pixels']=int(missing.sum());report['protected_reference_rectangle']=protected
    # Regenerate preview after restoring valid edge pixels.
    s=min(1,1800/final.shape[1]);preview=cv.resize(final,None,fx=s,fy=s,interpolation=cv.INTER_AREA)
    yy,xx=np.indices(preview.shape[:2]);bg=np.where((xx//16+yy//16)%2,42,64)
    alpha=preview[:,:,3:4]/255
    write_image(args.output/'local-seams-preview.jpg',(preview[:,:,:3]*alpha+bg[:,:,None]*(1-alpha)).astype(np.uint8))
    # Full-pixel provenance check, including warped pixels and exclusion masks.
    origin=np.array(report['outputs']['local-seams']['origin']);verified=0
    for i,((x,y),im,m) in enumerate(layers):
        oy,ox=np.where(owner==i+1);lx=ox+origin[0]-x;ly=oy+origin[1]-y
        assert (m[ly,lx]>0).all()
        if i:
            mx,my=maps[i-1];sx=np.rint(mx[ly,lx]).astype(int);sy=np.rint(my[ly,lx]).astype(int)
        else:sx,sy=lx,ly
        assert (masks[i][sy,sx]>0).all()
        assert np.array_equal(final[oy,ox,:3],images[i][sy,sx]),'Source pixels changed'
        verified+=len(ox)
    report['verification']={'exact_source_pixels_checked':verified,'status':'passed',
                            'scope':'Every visible local-seams pixel matches selected original RGB and is outside exclusion masks; geometry and mask completeness require visual review.'}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['verification'],flush=True)

if __name__=='__main__':main()
