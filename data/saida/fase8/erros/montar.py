import cv2, numpy as np, glob, sys
fs=sorted(glob.glob(sys.argv[1]))
tiles=[]
for f in fs:
    im=cv2.imread(f); h,w=im.shape[:2]
    im=im[int(h*0.45):, :]
    im=cv2.resize(im,(160,int(im.shape[0]*160/w)))
    lab=np.full((24,160,3),255,np.uint8); cv2.putText(lab,f.split('/')[-1][:2]+" "+f.split('_')[-2]+" "+f.split('_')[-1][:2],(2,17),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,255),1)
    tiles.append(np.vstack([lab,im]))
H=max(t.shape[0] for t in tiles)
tiles=[np.pad(t,((0,H-t.shape[0]),(0,4),(0,0)),constant_values=255) for t in tiles]
rows=[np.hstack(tiles[i:i+8]+[np.full_like(tiles[0],255)]*(8-len(tiles[i:i+8]))) for i in range(0,len(tiles),8)]
cv2.imwrite(sys.argv[2],np.vstack(rows)); print(len(fs))
