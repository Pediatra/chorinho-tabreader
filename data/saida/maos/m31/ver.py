import cv2, numpy as np, sys
def r(x,w=900): return cv2.resize(x,(w,int(x.shape[0]*w/x.shape[1])))
ims=[r(cv2.imread(p)) for p in sys.argv[2:]]
cv2.imwrite(sys.argv[1], np.vstack(ims))
