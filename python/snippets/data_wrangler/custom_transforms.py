######################################################
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

col = 'eventId'
dum = pd.get_dummies(df[col]).values

dum = np.round(PCA(n_components=3).fit_transform(dum),2)
dum = pd.DataFrame(dum, columns=[col+'_'+str(i) for i in range(dum.shape[1])]).reset_index(drop=True)
df = df.reset_index(drop=True).join(dum,how='inner')
######################################################
