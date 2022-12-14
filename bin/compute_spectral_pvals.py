import numpy as np
import pandas as pd
from tqdm import tqdm,tqdm_notebook, tqdm_pandas
import os
import glob
import pickle
import argparse

#### computation of spectral (optimized) p-values
##### work in progress to appear in upcoming submission


## Outputs:
### p-values tsv file at args.outfldr+'/spectral_pvalues.tsv'
### if save_c_f flag, then can read in optimizing c and f as below:
#### with open(args.outfldr+'/spectral_cj.npy','rb') as f:
####     a = np.load(f)
#### with open(args.outfldr+'/spectral_f.pkl', 'rb') as handle:
####     b = pickle.load(handle)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument( ### input abundant_stratified_{}.txt.gz folder 
        "--strat_fldr",
        type=str
    )
    parser.add_argument( ### input anchors_pvals.tsv file, for sample names and ordering 
        "--anchors_pvals",
        type=str
    )
    parser.add_argument( ### target output folder, required
        "--outfldr",
        type=str
    )
    parser.add_argument( ### samplesheet file, if samplesheet-based cj are to be used
        "--samplesheet",
        type=str,
        default=""
    )
    parser.add_argument( ### samplesheet file, if samplesheet-based cj are to be used
        "--anchor_list",
        type=str,
        default=""
    )
    parser.add_argument( ### flag, whether to save cj or not
        "--save_c_f",
        type=bool,
        default=False
    )
    args = parser.parse_args()
    return args


### read in samplsheet, and output samplesheetCj (properly ordered)
def parseSamplesheet(args,sampleNames):
    sheetCj = np.ones(len(sampleNames))
    if args.samplesheet!='':
        with open(args.samplesheet,'r') as f:
            cols = f.readline().split(',')
        if len(cols)==1: ### if len(cols) is 1, then only samplesheet name, no ids
            print("Only 1 samplesheet column, using random cjs")
        elif len(cols)>2:
            print("Improperly formatted samplesheet")
        else:

            sheetdf = pd.read_csv(args.samplesheet,names=['fname','sheetCjs'])
            sheetdf['sample'] = (sheetdf.fname
                            .str.rsplit('/',1,expand=True)[1]
                            .str.split('.',1,expand=True)[0])
            sheetdf = sheetdf.drop(columns='fname')
            sheetdf['sheetCjs'] = normalizevec(sheetdf.sheetCjs)

            sheetCj = sheetdf.set_index('sample').T[sampleNames].to_numpy().flatten()
    return sheetCj

### construct contingency tables, only for anchors in anchLst
def constructCountsDf(strat_fldr,anchLst):
    kmer_size = 27
    dfs = []
    paths = glob.glob(strat_fldr+"/abundant_stratified_*.txt.gz")
    print('reading in abudant_stratified files')
    for path in tqdm(paths,total=len(paths)):
        df = pd.read_csv(path.strip(), delim_whitespace=True, names=['counts','seq','sample'])
        df['anchor'] = df.seq.str[:kmer_size]
        df['target'] = df.seq.str[kmer_size:]
        df = df.drop(columns='seq').drop_duplicates()
        if anchLst != []:
            df = df[df.anchor.isin(anchLst)]
        dfs.append(df)

    print('concat and pivoting')
    ctsDf = pd.concat(dfs)
    ctsDf = (ctsDf
        .pivot(index=['anchor', 'target'], columns='sample', values='counts')
        .reset_index()
        .fillna(0))
    return ctsDf

### split contingency table into train and test data
def splitCounts(mat,downSampleFrac = .5): #slight modification of https://stackoverflow.com/questions/11818215/subsample-a-matrix-python
    keys, counts = zip(*[
    ((i,j), mat[i,j])
        for i in range(mat.shape[0])
        for j in range(mat.shape[1])
        if mat[i,j] > 0
    ])
    # Make the cumulative counts array
    counts = np.array(counts, dtype=np.int64)
    sum_counts = np.cumsum(counts)

    # Decide how many counts to include in the sample
    frac_select = downSampleFrac
    count_select = int(sum_counts[-1] * frac_select)

    # Choose unique counts
    ind_select = sorted(np.random.choice(range(sum_counts[-1]), count_select,replace=False))

    # A vector to hold the new counts
    out_counts = np.zeros(counts.shape, dtype=np.int64)

    # Perform basically the merge step of merge-sort, finding where
    # the counts land in the cumulative array
    i = 0
    j = 0
    while i<len(sum_counts) and j<len(ind_select):
        if ind_select[j] < sum_counts[i]:
            j += 1
            out_counts[i] += 1
        else:
            i += 1

    # Rebuild the matrix using the `keys` list from before
    out_mat = np.zeros(mat.shape, dtype=np.int64)
    for i in range(len(out_counts)):
        out_mat[keys[i]] = out_counts[i]
        
    return out_mat

### shift and scale an input vector to be in the range [minval, maxval]
def normalizevec(x,minval=0,maxval=1):
    x = np.array(x)
    x01= (x-x.min())/(x.max()-x.min())
    return x01*(maxval-minval)+minval

### find locally-optimal (unconstrained) c and f from spectral c initialization
def generateSpectralOptcf(X,tblShape):
    np.random.seed(0)### for filling in f
    
    relevantTargs = X.sum(axis=1)>0
    relevantSamples = X.sum(axis=0)>0
    
    if relevantTargs.sum()<2 or relevantSamples.sum()<2:
        print('error')
        return

    X = X[np.ix_(relevantTargs,relevantSamples)]

    
    ###### Spectral initialization of c
    ### pairwise similarity matrix
    A = X.T @ X
    A = A-np.diag(np.diag(A))
    
    ### remove isolated elements
    sampleMask2= (A.sum(axis=0)>0)
    
    if sampleMask2.sum()==0: ### graph is unconnected (I think)
        sampleMask2 = np.ones(X.shape[1],dtype='bool')
        c = np.random.choice([-1,1],size=X.shape[1])
    else:
        A = A[np.ix_(sampleMask2,sampleMask2)]
        X = X[:,sampleMask2]

        ## construct diagonals for Laplacian
        D = np.diag(A.sum(axis=0))

        ### spectrally normalized Laplacian
        Dnorm = np.diag(A.sum(axis=0)**(-1/2))
        L = np.eye(A.shape[0]) - Dnorm@A@Dnorm

        ### normal
        # L=D-A

        ### potentially could merge results from 2 clusterings?

        ### compute fiedler vector
        eigvals,eigvecs =np.linalg.eig(L)
        c = np.sign(normalizevec(np.real(eigvecs[:,np.argsort(np.abs(eigvals))[1]])))
        ## maybe more fancy checking needed if graph isn't connected
    
    #### if clustering put all samples in same cluster, shouldn't happen
    if np.all(c==c[0]):
        c[0] = -1*c[0]
    
    nj = X.sum(axis=0)
    njinvSqrt = 1.0/np.maximum(1,np.sqrt(nj)) ### avoid divide by 0 errors
    njinvSqrt[nj==0]=0
    
    fOpt = np.sign((X-X@np.outer(np.ones(X.shape[1]),nj)/np.maximum(1,X.sum()))@(c*njinvSqrt))
    fOpt = (fOpt+1)/2 ### to rescale f to be [0,1] valued
    
    Sold = 0
    i=0
    while True:
        
        ### find optimal f for fixed c
        fOpt = np.sign((X-X@np.outer(np.ones(X.shape[1]),nj)/np.maximum(1,X.sum()))@(c*njinvSqrt))
        fOpt = (fOpt+1)/2 ### to rescale f to be [0,1] valued
        fOpt=normalizevec(fOpt)
        
        ### find optimal c for fixed f
        Sj = np.multiply(fOpt @ (X-X@np.outer(np.ones(X.shape[1]),nj)/X.sum()),njinvSqrt)
        c = Sj/np.linalg.norm(Sj,2)
        
        ### compute objective value, if fixed, stop
        S = fOpt @ (X-X@np.outer(np.ones(X.shape[1]),nj)/X.sum())@(c*njinvSqrt)/np.linalg.norm(c,2)
        if S==Sold: ### will terminate once fOpt is fixed over 2 iterations
            break
        Sold = S
        i+=1
        if i>50: ### something went wrong
            c = np.zeros_like(c)
            fOpt=np.zeros_like(fOpt)
            break
    
    ## extend to targets and samples that didn't occur in training data
    fElong = np.random.choice([0,1],size=tblShape[0])
    fElong[relevantTargs] = fOpt
    fOpt = fElong
    
    cElong = np.zeros(tblShape[1])
    cElong[np.arange(tblShape[1])[relevantSamples][sampleMask2]]=c ### fancy indexing
    cOpt = cElong
    
    return np.nan_to_num(cOpt,0),np.nan_to_num(normalizevec(fOpt),0),i


### find locally-optimal (unconstrained) c and f from random initialization
def generateRandOptcf(X,tblShape,randSeed=0):
    np.random.seed(randSeed) ### random initialization and extension
    
    relevantTargs = X.sum(axis=1)>0
    relevantSamples = X.sum(axis=0)>0
    
    if relevantTargs.sum()<2 or relevantSamples.sum()<2:
        print('error')
        return

    X = X[np.ix_(relevantTargs,relevantSamples)]
    
    c = np.random.choice([-1,1],size=X.shape[1])
    #### if clustering put all in same cluster, perturb
    
    if np.all(c==c[0]):
        c[0] = -1*c[0]
    
    nj = X.sum(axis=0)
    njinvSqrt = 1.0/np.maximum(1,np.sqrt(nj)) ### avoid divide by 0 errors
    njinvSqrt[nj==0]=0
    
    fOpt = np.sign((X-X@np.outer(np.ones(X.shape[1]),nj)/np.maximum(1,X.sum()))@(c*njinvSqrt))
    fOpt = (fOpt+1)/2 ### to rescale f to be [0,1] valued
    
    Sold = 0
    i=0
    while True:
        
        ### find optimal f for fixed c
        fOpt = np.sign((X-X@np.outer(np.ones(X.shape[1]),nj)/np.maximum(1,X.sum()))@(c*njinvSqrt))
        fOpt = (fOpt+1)/2 ### to rescale f to be [0,1] valued
        
        ### find optimal c for fixed f
        Sj = np.multiply(fOpt @ (X-X@np.outer(np.ones(X.shape[1]),nj)/X.sum()),njinvSqrt)
        c = Sj/np.linalg.norm(Sj,2)
        
        ### compute objective value, if fixed, stop
        S = fOpt @ (X-X@np.outer(np.ones(X.shape[1]),nj)/X.sum())@(c*njinvSqrt)/np.linalg.norm(c,2)
        if S==Sold: ### will terminate once fOpt is fixed over 2 iterations
            break
        Sold = S
        i+=1
        if i>50:
            c = np.zeros_like(c)
            fOpt=np.zeros_like(fOpt)
            break
    
    
    ## extend to targets and samples that didn't occur previously
    fElong = np.random.choice([0,1],size=tblShape[0])
    fElong[relevantTargs] = fOpt
    fOpt = fElong
    
    cElong = np.zeros(tblShape[1])
    cElong[np.arange(tblShape[1])[relevantSamples]]=c ### fancy indexing
    cOpt = cElong
    
    return cOpt,fOpt,i

### find locally-optimal c and f from random initialization
#### constrained to c having the same sign as sheetCj

def generateSignedSheetCjOptcf(X,sheetCj,tblShape):
    np.random.seed(0)### for filling in f
    
    relevantTargs = X.sum(axis=1)>0
    relevantSamples = X.sum(axis=0)>0

    X = X[np.ix_(relevantTargs,relevantSamples)]

    cSign = sheetCj[relevantSamples]
    c = cSign

    
    nj = X.sum(axis=0)
    njinvSqrt = 1.0/np.maximum(1,np.sqrt(nj)) ### avoid divide by 0 errors
    njinvSqrt[nj==0]=0
    
    fOpt = np.sign((X-X@np.outer(np.ones(X.shape[1]),nj)/np.maximum(1,X.sum()))@(c*njinvSqrt))
    fOpt = (fOpt+1)/2 ### to rescale f to be [0,1] valued
    
    Sold = 0
    i=0
    while True:
        
        ### find optimal f for fixed c
        fOpt = np.sign((X-X@np.outer(np.ones(X.shape[1]),nj)/np.maximum(1,X.sum()))@(c*njinvSqrt))
        fOpt = (fOpt+1)/2 ### to rescale f to be [0,1] valued
        
        ### find optimal c for fixed f
        Sj = np.multiply(fOpt @ (X-X@np.outer(np.ones(X.shape[1]),nj)/X.sum()),njinvSqrt)
#         c = Sj/np.abs(Sj).sum()
        ### construct plus and minus variants of Sj
        cplus = Sj * ((Sj*cSign) >0)
        cplus /= np.maximum(1,np.linalg.norm(cplus,2))
        c=cplus
        Splus = fOpt @ (X-X@np.outer(np.ones(X.shape[1]),nj)/X.sum())@(c*njinvSqrt)/np.maximum(1,np.linalg.norm(c,2))
        
        cminus = Sj * ((Sj*cSign) <0)
        cminus /= np.maximum(1,np.linalg.norm(cminus,2))
        c=cminus
        Sminus = fOpt @ (X-X@np.outer(np.ones(X.shape[1]),nj)/X.sum())@(c*njinvSqrt)/np.maximum(1,np.linalg.norm(c,2))

        if Splus >= -1*Sminus:
            c = cplus
            S = Splus
        else:
            c = cminus
            S = Sminus

        if S==Sold: ### will terminate once fOpt is fixed over 2 iterations
            break
        Sold = S
        i+=1
        if i>50:
            c = np.zeros_like(c)
            fOpt=np.zeros_like(fOpt)
            break
            
    ## extend to targets and samples that didn't occur previously
    fElong = np.random.choice([0,1],size=tblShape[0])
    fElong[relevantTargs] = fOpt
    fOpt = fElong
    
    cElong = np.zeros(tblShape[1])
    cElong[np.arange(tblShape[1])[relevantSamples]]=c ### fancy indexing
    cOpt = cElong
    return cOpt,fOpt,i

### find optimal f for given input sheetCj
def generateSheetCjOptcf(X,sheetCj,tblShape):
    np.random.seed(0) ### for filling in f
    
    relevantTargs = X.sum(axis=1)>0
    X = X[relevantTargs]

    ## set cj as sheetCj
    c = sheetCj

    nj = X.sum(axis=0)
    njinvSqrt = 1.0/np.maximum(1,np.sqrt(nj)) ### avoid divide by 0 errors
    njinvSqrt[nj==0]=0
    
    ## compute opt f
    fOpt = np.sign((X-X@np.outer(np.ones(X.shape[1]),nj)/np.maximum(1,X.sum()))@(c*njinvSqrt))
    fOpt = (fOpt+1)/2 ### to rescale f to be [0,1] valued
    
    ## extend to targets and samples that didn't occur previously
    fElong = np.random.choice([0,1],size=tblShape[0])
    fElong[relevantTargs] = fOpt
    fOpt = fElong
    
    cOpt = c ### sheetCj
    return cOpt,fOpt

### for split data matrix, test p-value
### Xtest passed in
def testPval(X,cOpt,fOpt):
    if (cOpt==0).all():
        return 1
    
    cOpt = np.nan_to_num(cOpt,0)
    fOpt = np.nan_to_num(fOpt,0)
    if not (fOpt.max()<=1) and (fOpt.min()>=0):
        fOpt = normalizevec(np.nan_to_num(fOpt,0))
    
    ### only requirement for valid p-value
    assert((fOpt.max()<=1) and (fOpt.min()>=0))
    nj = X.sum(axis=0)
    njinvSqrt = 1.0/np.maximum(1,np.sqrt(nj))
    njinvSqrt[nj==0]=0
    
    ### compute p value
    S = fOpt @ (X-X@np.outer(np.ones(X.shape[1]),nj)/X.sum())@(cOpt*njinvSqrt)
    M=X.sum()
    num = (cOpt**2).sum()*M 
    denom=(cOpt@np.sqrt(nj))**2
    with np.errstate(divide='ignore', invalid='ignore'):
        a = 1.0/(np.sqrt(num/denom)+1.0)
        term1HC = 2*np.exp(- 2*(1-a)**2*S**2
                       /(cOpt**2).sum())
        term2HC = 2*np.exp(-2*a**2*M*S**2
                           /(cOpt@np.sqrt(nj))**2 )

    if a==0:
        pv = term1HC
    else:
        pv = term1HC+term2HC
        
    return min(1,pv)


def effectSize(X,c,f):
    ### binary effect size
    effectBin = np.abs(f@X@(c>0) / (X@(c>0)).sum() - f@X@(c<0) / (X@(c<0)).sum())
    if (c>0).sum()==0 or (c<0).sum()==0:
        effectBin = 0

    ### new effect size definition
    effectRaw = np.abs(f@X@c / (X@np.abs(c)).sum())

    return effectBin,effectRaw


#### main function
def main():
    args = get_args()

    if not os.path.exists(args.outfldr):
        os.makedirs(args.outfldr)

    pvalsdf = pd.read_csv(args.anchors_pvals,sep='\t')
    print('read pvals df')

    if args.anchor_list!='':
        print("using passed in anchor list")
        anchLst = pd.read_csv(args.anchor_list,names=['anchor']).anchor.to_list()
        if len(anchLst)==0:
            print('no anchors in list')
            return
        print(len(anchLst), "anchors")
    else:
        print('using all anchors')
        anchLst = []

    print('constructing counts dataframe')
    ctsDf = constructCountsDf(args.strat_fldr,anchLst)
    print('done with counts dataframe')

    if anchLst == []:
        anchLst = ctsDf.reset_index().anchor.unique()
        print('generated all anchors, ', len(anchLst))

    sampleNames = (pvalsdf.columns[pvalsdf.columns.str.startswith('cj_rand')]
                .str.lstrip('cj_rand_opt_').to_list())

    sheetCj = parseSamplesheet(args,sampleNames)

    useSheetCj = not np.all(sheetCj==sheetCj[0])
    ctsDf = ctsDf.loc[:,['anchor','target']+sampleNames].set_index('anchor')
    

    ### new version
    # start = time.time()
    readMinimum = 10
    trainFrac=.5
    pvalsSpectral = np.ones(len(anchLst))
    pvalsRandOpt = np.ones(len(anchLst))
    pvalsSheet=np.ones(len(anchLst))
    pvalsSheetSign=np.ones(len(anchLst))

    eSizeArr = np.zeros((len(anchLst),8))
    iArr = np.zeros(len(anchLst))
    if args.save_c_f:
        cjArr = np.zeros((len(anchLst),4,len(sampleNames)))
        fArr = [[] for _ in range(4)] ### matrices are different sizes

    anchsUsed = np.ones(len(anchLst),dtype='bool')
    for anch_idx,anch in tqdm(enumerate(anchLst),total=len(anchLst)):
        if anch not in ctsDf.index:
            print('anchor not present', anch)
            anchsUsed[anch_idx]=False
            continue

        ### load in data matrix
        ctsLoad = ctsDf.loc[anch,sampleNames].to_numpy()
        
        if ctsLoad.sum()<readMinimum or len(ctsLoad.shape)==1 or ctsLoad.shape[0] <=1 or ctsLoad.shape[1]<=1:
            continue

        np.random.seed(0)
        X = splitCounts(ctsLoad,trainFrac) ## fraction to be used for "training"
        Xtrain = X
        Xtest = ctsLoad-Xtrain
        
        relevantTargs = Xtrain.sum(axis=1)>0
        relevantSamples = Xtrain.sum(axis=0)>0
        
        if relevantTargs.sum()<2 or relevantSamples.sum()<2:
            continue
            
        cOpt,fOpt,num_iters = generateSpectralOptcf(Xtrain,ctsLoad.shape)
        pvalsSpectral[anch_idx]=testPval(Xtest,cOpt,fOpt)
        eSizeArr[anch_idx,[0,1]]=effectSize(ctsLoad,cOpt,fOpt)
        if args.save_c_f:
            cjArr[anch_idx,0]=cOpt
            fArr[0].append(fOpt)
        # pvalsSpectral[anch_idx]=testPval(ctsLoad,cOpt,fOpt) ##########can construct data-snooping p-values############


        cOpt,fOpt,num_iters = generateRandOptcf(Xtrain,ctsLoad.shape)
        pvalsRandOpt[anch_idx]=testPval(Xtest,cOpt,fOpt)
        eSizeArr[anch_idx,[2,3]]=effectSize(ctsLoad,cOpt,fOpt)
        if args.save_c_f:
            cjArr[anch_idx,1]=cOpt
            fArr[1].append(fOpt)
        # pvalsRandOpt[anch_idx]=testPval(ctsLoad,cOpt,fOpt) ######## can construct data-snooping p-values ###########
    
        if useSheetCj:
            cOpt,fOpt,num_iters = generateSignedSheetCjOptcf(Xtrain,sheetCj,ctsLoad.shape)
            pvalsSheetSign[anch_idx]=testPval(Xtest,cOpt,fOpt)
            eSizeArr[anch_idx,[4,5]]=effectSize(ctsLoad,cOpt,fOpt)
            if args.save_c_f:
                cjArr[anch_idx,2]=cOpt
                fArr[2].append(fOpt)
            print(cOpt,eSizeArr[anch_idx,[4,5]])
            
            cOpt,fOpt = generateSheetCjOptcf(Xtrain,sheetCj,ctsLoad.shape)
            pvalsSheet[anch_idx]=testPval(Xtest,cOpt,fOpt)
            eSizeArr[anch_idx,[6,7]]=effectSize(ctsLoad,cOpt,fOpt)
            if args.save_c_f:
                cjArr[anch_idx,3]=cOpt
                fArr[3].append(fOpt)

    if useSheetCj:
        outdf = pd.DataFrame({'anchor':anchLst, 'pval_spectral':pvalsSpectral, 'pval_rand_init_EM':pvalsRandOpt,
        'pvals_optimized_samplesheetSigned':pvalsSheetSign, 'pvals_optimized_samplesheet':pvalsSheet})
        outdf['minpv'] = np.asarray([pvalsSpectral,pvalsRandOpt,pvalsSheetSign,pvalsSheet]).min(axis=0)
    else:
        outdf = pd.DataFrame({'anchor':anchLst, 'pvalsSpectral':pvalsSpectral, 'pvalsRandOpt':pvalsRandOpt})
        outdf['minpv'] = np.asarray([pvalsSpectral,pvalsRandOpt]).min(axis=0)

    outdf['effect_size_binary_spectral'] = eSizeArr[:,0]
    outdf['effect_size_spectral'] =eSizeArr[:,1]
    outdf['effect_size_binary_rand_init_EM'] = eSizeArr[:,2]
    outdf['effect_size_rand_init_EM'] = eSizeArr[:,3]
    if useSheetCj:
        outdf['effect_size_binary_optimized_samplesheetSigned']=eSizeArr[:,4]
        outdf['effect_size_optimized_samplesheetSigned']=eSizeArr[:,5]
        outdf['effect_size_binary_optimized_samplesheet']=eSizeArr[:,6]
        outdf['effect_size_optimized_samplesheet']=eSizeArr[:,7]

    print(eSizeArr[anchsUsed.astype('bool')])

    outdf = outdf[anchsUsed.astype('bool')]
    outdf = outdf.sort_values('minpv').drop(columns=['minpv'])
    outdf.to_csv(args.outfldr+'/spectral_pvalues.tsv', sep='\t', index=False)


    if args.save_c_f:
        if not useSheetCj:
            fArr = fArr[[0,1]]
            cjArr = cjArr[:,:4]
        cjArr = cjArr[anchsUsed]
        with open(args.outfldr+'/spectral_cj.npy', 'wb') as f:
            np.save(f,cjArr)

        with open(args.outfldr+'/spectral_f.pkl', 'wb') as handle:
            pickle.dump(fArr, handle, protocol=pickle.HIGHEST_PROTOCOL)

        #### to be read in as below
        # with open(args.outfldr+'/spectral_cj.npy','rb') as f:
        #     a = np.load(f)
        # with open(args.outfldr+'/spectral_f.pkl', 'rb') as handle:
        #     b = pickle.load(handle)


print('starting spectral p value computation')
main()