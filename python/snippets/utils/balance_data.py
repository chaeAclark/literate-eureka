def balance_data(X, y, level=0, max_n=None):
    val = Counter(y).most_common()[-level-1][1]
    if max_n is not None:
        val = int(np.min([val, max_n]))
    Xs = []
    ys = []
    for lbl in dict(Counter(y)).keys(): 
        X_lbl = [v for i,v in enumerate(X) if y[i]==lbl]
        idx = np.random.choice(len(X_lbl), np.min([len(X_lbl),val]), replace=False)
        Xs.extend([X_lbl[i] for i in idx])
        ys.extend([lbl for _ in range(len(idx))])
    temp = list(zip(Xs, ys))
    random.shuffle(temp)
    Xs, ys = zip(*temp)
    return list(Xs),list(ys)

  
def balance_dataframe(df, lbl_col, level=0, max_n=None):
    if df.index.name is None:
        index_col = 'index'
    else:
        index_col = df.index.name
    df = df.reset_index(drop=False)
    columns = [c for c in df.columns if c != lbl_col]
    X = df[columns].values
    y = df[lbl_col].values#[:,None]
    X,y = balance_data(X, y, level=level, max_n=max_n)
    if len(X[0]) <= 1:
        raise NotImplementedError(f'this method does not yet support too few features X:{len(X[0])} must be >= 2!')
    data = np.hstack([np.asarray(y)[:,None],np.asarray(X)])
    df = pd.DataFrame(data,columns=[lbl_col]+columns).set_index(index_col)
    return df
