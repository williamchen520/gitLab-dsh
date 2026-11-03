#!/usr/bin/env python
# coding: utf-8

# In[1]:

# 安装必要的库
get_ipython().system('pip install pandas')
get_ipython().system('pip install numpy')
get_ipython().system('pip install scikit-learn')
get_ipython().system('pip install rdkit')
get_ipython().system('pip install matplotlib')
get_ipython().system('pip install seaborn')
get_ipython().system('pip install shap')  # 新增SHAP库

# In[2]:

# 导入库
import pandas as pd
print(f'pandas: {pd.__version__}')
import numpy as np
print(f'numpy: {np.__version__}')
import matplotlib.pyplot as plt
get_ipython().run_line_magic('matplotlib', 'inline')
import shap  # 导入SHAP
shap.initjs()  # 初始化SHAP的JS可视化

# In[3]:

def data(path):
    """加载数据函数"""
    data_featurized = pd.read_csv(path)
    y = data_featurized['Category']
    X = data_featurized.drop(['Category'], axis=1)
    return X, y

# In[4]:

# 数据路径
path_three_class = 'ip_train_three_class.csv'  # 三分类训练数据
path_two_class = 'ip_train_two_class.csv'      # 二分类训练数据

# 加载数据
X_three, Y_three = data(path_three_class)
X_two, Y_two = data(path_two_class)

# In[5]:

# 显示当前工作目录
pwd

# In[6]:

# 查看数据
X_three.head()

# In[7]:

Y_three.head()

# In[8]:

X_two.head()

# In[9]:

Y_two.head()

# In[10]:

import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import make_scorer, matthews_corrcoef, balanced_accuracy_score, accuracy_score
from sklearn.model_selection import cross_validate
from sklearn.model_selection import RepeatedStratifiedKFold

# In[11]:

def randomforestclassifier(X, y, model_name=""):
    """
    随机森林分类器训练函数
    新增：返回训练数据用于SHAP分析
    """
    # 定义评估指标
    scoring = {
        'accuracy': make_scorer(accuracy_score),
        'balanced_accuracy': make_scorer(balanced_accuracy_score),
        'f1_macros': 'f1_macro',
        'MCC': make_scorer(matthews_corrcoef)
    }

    scores = []  # 存储平均分数
    scores_std = []  # 存储标准差

    # 定义模型参数
    model = RandomForestClassifier(
        n_jobs=-1,
        random_state=42,
        n_estimators=725,
        max_depth=32,
        min_samples_split=2,
        min_samples_leaf=1
    )

    print(f'开始{model_name}模型的交叉验证...')

    # 10折分层交叉验证
    cv = RepeatedStratifiedKFold(n_splits=10, n_repeats=1, random_state=42)
    n_scores = cross_validate(model, X, y, scoring=scoring, cv=cv)
    
    print(f'{model_name}模型交叉验证完成...')
    print('保存分数...')

    # 提取分数
    scores.append(np.mean(n_scores['test_accuracy']))
    scores_std.append(np.std(n_scores['test_accuracy']))
    accuracy = n_scores['test_accuracy']

    scores.append(np.mean(n_scores['test_balanced_accuracy']))
    scores_std.append(np.std(n_scores['test_balanced_accuracy']))
    balanced_accuracy = n_scores['test_balanced_accuracy']

    scores.append(np.mean(n_scores['test_f1_macros']))
    scores_std.append(np.std(n_scores['test_f1_macros']))
    f1 = n_scores['test_f1_macros']

    scores.append(np.mean(n_scores['test_MCC']))
    scores_std.append(np.std(n_scores['test_MCC']))
    MCC = n_scores['test_MCC']

    print('分数已保存...')

    # 在整个训练集上拟合模型
    model.fit(X, y)
    
    # 创建SHAP解释器
    print(f'创建{model_name}模型的SHAP解释器...')
    explainer = shap.TreeExplainer(model)
    
    # 计算训练数据的SHAP值（用于全局解释）
    print(f'计算{model_name}模型的SHAP值...')
    shap_values_train = explainer.shap_values(X)
    
    return scores, scores_std, model, accuracy, balanced_accuracy, f1, MCC, explainer, shap_values_train

# In[12]:

def run_model(path, model_name=""):
    """运行模型训练流程"""
    X_train, y_train = data(path)
    cross_validation_scores, scores_std, model, accuracy, balanced_accuracy, f1, MCC, explainer, shap_values_train = randomforestclassifier(X_train, y_train, model_name)

    print(f'{model_name}模型交叉验证准确率: {cross_validation_scores[0]:.4f} +/- {scores_std[0]:.4f}')
    print(f'{model_name}模型交叉验证平衡准确率: {cross_validation_scores[1]:.4f} +/- {scores_std[1]:.4f}')
    print(f'{model_name}模型交叉验证F1分数: {cross_validation_scores[2]:.4f} +/- {scores_std[2]:.4f}')
    print(f'{model_name}模型交叉验证MCC: {cross_validation_scores[3]:.4f} +/- {scores_std[3]:.4f}')

    return cross_validation_scores, model, accuracy, balanced_accuracy, f1, MCC, explainer, shap_values_train

# In[13]:

# 训练两个模型
print("开始训练三分类模型...")
_, model_three_class, _, _, _, _, explainer_three_class, shap_values_three_train = run_model(path_three_class, "三分类")

print("\n开始训练二分类模型...")
_, model_two_class, _, _, _, _, explainer_two_class, shap_values_two_train = run_model(path_two_class, "二分类")

# In[14]:

# 保存模型和解释器
filename_three_class = 'ip_three_class_final_model.sav'
filename_two_class = 'ip_two_class_final_model.sav'

# 保存模型
pickle.dump(model_three_class, open(filename_three_class, 'wb'))
pickle.dump(model_two_class, open(filename_two_class, 'wb'))

# 保存SHAP解释器（可选）
filename_explainer_three = 'ip_three_class_explainer.sav'
filename_explainer_two = 'ip_two_class_explainer.sav'
pickle.dump(explainer_three_class, open(filename_explainer_three, 'wb'))
pickle.dump(explainer_two_class, open(filename_explainer_two, 'wb'))

print("模型和SHAP解释器已保存")

# In[15]:

import pickle

# In[16]:

def load_model(filepath):
    """加载模型函数"""
    model = pickle.load(open(filepath, 'rb'))
    return model

def load_explainer(filepath):
    """加载SHAP解释器函数"""
    explainer = pickle.load(open(filepath, 'rb'))
    return explainer

# In[17]:

# 加载模型和解释器
filepath_three_class = 'ip_three_class_final_model.sav'
filepath_two_class = 'ip_two_class_final_model.sav'
filepath_explainer_three = 'ip_three_class_explainer.sav'
filepath_explainer_two = 'ip_two_class_explainer.sav'

model_three_class = load_model(filepath_three_class)
model_two_class = load_model(filepath_two_class)
explainer_three_class = load_explainer(filepath_explainer_three)
explainer_two_class = load_explainer(filepath_explainer_two)

print("模型和SHAP解释器已加载")

# In[18]:

from rdkit import Chem 
from rdkit.Chem import Descriptors

# In[19]:

def featurize_three_class(linker):
    """三分类模型特征化函数"""
    try:
        m = Chem.MolFromSmiles(linker)
        if m is None:
            print(f"警告：无法解析SMILES: {linker}")
            return None
        
        # 计算所有描述符
        EState_VSA1 = Descriptors.EState_VSA1(m) 
        EState_VSA2 = Descriptors.EState_VSA2(m)
        EState_VSA4 = Descriptors.EState_VSA4(m)
        EState_VSA5 = Descriptors.EState_VSA5(m)
        EState_VSA6 = Descriptors.EState_VSA6(m)
        EState_VSA7 = Descriptors.EState_VSA7(m)
        EState_VSA8 = Descriptors.EState_VSA8(m)
        EState_VSA9 = Descriptors.EState_VSA9(m)
        EState_VSA10 = Descriptors.EState_VSA10(m)
        VSA_EState1 = Descriptors.VSA_EState1(m)
        VSA_EState2 = Descriptors.VSA_EState2(m)
        VSA_EState3 = Descriptors.VSA_EState3(m)
        VSA_EState5 = Descriptors.VSA_EState5(m)
        VSA_EState6 = Descriptors.VSA_EState6(m)
        VSA_EState8 = Descriptors.VSA_EState8(m)
        VSA_EState9 = Descriptors.VSA_EState9(m)
        QED = Descriptors.qed(m)
        Chi0 = Descriptors.Chi0(m)
        Chi0n = Descriptors.Chi0n(m)
        Chi0v = Descriptors.Chi0v(m)
        Chi1 = Descriptors.Chi1(m)
        Chi1n = Descriptors.Chi1n(m)
        Chi1v = Descriptors.Chi1v(m)
        Chi2n = Descriptors.Chi2n(m)
        Chi3n = Descriptors.Chi3n(m)
        Chi3v = Descriptors.Chi3v(m)
        Chi4n = Descriptors.Chi4n(m)
        Chi4v = Descriptors.Chi4v(m)
        HallKierAlpha = Descriptors.HallKierAlpha(m)
        Kappa1 = Descriptors.Kappa1(m)
        Kappa2 = Descriptors.Kappa2(m)
        MinAbsPartialCharge = Descriptors.MinAbsPartialCharge(m)
        FpDensityMorgan2 = Descriptors.FpDensityMorgan2(m)
        FpDensityMorgan3 = Descriptors.FpDensityMorgan3(m)
        FpDensityMorgan1 = Descriptors.FpDensityMorgan1(m)
        HeavyAtomMolWt = Descriptors.HeavyAtomMolWt(m)
        ExactMolWt = Descriptors.ExactMolWt(m)
        MolWt = Descriptors.MolWt(m)
        NumValenceElectrons = Descriptors.NumValenceElectrons(m)
        MaxPartialCharge = Descriptors.MaxPartialCharge(m)
        MolMR = Descriptors.MolMR(m)
        LabuteASA = Descriptors.LabuteASA(m)
        PEOE_VSA1 = Descriptors.PEOE_VSA1(m)
        PEOE_VSA2 = Descriptors.PEOE_VSA2(m)
        PEOE_VSA3 = Descriptors.PEOE_VSA3(m)
        PEOE_VSA9 = Descriptors.PEOE_VSA9(m)
        PEOE_VSA10 = Descriptors.PEOE_VSA10(m)
        PEOE_VSA11 = Descriptors.PEOE_VSA11(m)
        PEOE_VSA13 = Descriptors.PEOE_VSA13(m)
        PEOE_VSA14 = Descriptors.PEOE_VSA14(m)
        SMR_VSA1 = Descriptors.SMR_VSA1(m)
        SMR_VSA2 = Descriptors.SMR_VSA2(m)
        SMR_VSA3 = Descriptors.SMR_VSA3(m)
        SMR_VSA4 = Descriptors.SMR_VSA4(m)
        SMR_VSA5 = Descriptors.SMR_VSA5(m)
        SMR_VSA6 = Descriptors.SMR_VSA6(m)
        SMR_VSA7 = Descriptors.SMR_VSA7(m)
        SMR_VSA10 = Descriptors.SMR_VSA10(m)
        SlogP_VSA2 = Descriptors.SlogP_VSA2(m)
        SlogP_VSA3 = Descriptors.SlogP_VSA3(m)
        SlogP_VSA4 = Descriptors.SlogP_VSA4(m)
        SlogP_VSA5 = Descriptors.SlogP_VSA5(m)
        SlogP_VSA6 = Descriptors.SlogP_VSA6(m)
        SlogP_VSA8 = Descriptors.SlogP_VSA8(m)
        TPSA = Descriptors.TPSA(m)
        MaxAbsEStateIndex = Descriptors.MaxAbsEStateIndex(m)
        MaxEStateIndex = Descriptors.MaxEStateIndex(m)
        MinEStateIndex = Descriptors.MinEStateIndex(m)
        fr_Al_OH = Descriptors.fr_Al_OH(m)
        fr_Al_OH_noTert = Descriptors.fr_Al_OH_noTert(m)
        fr_ArN = Descriptors.fr_ArN(m)
        fr_Ar_N = Descriptors.fr_Ar_N(m)
        fr_C_O = Descriptors.fr_C_O(m)
        fr_C_O_noCOO = Descriptors.fr_C_O_noCOO(m)
        fr_NH0 = Descriptors.fr_NH0(m)
        fr_Ndealkylation1 = Descriptors.fr_Ndealkylation1(m)
        fr_alkyl_halide = Descriptors.fr_alkyl_halide(m)
        fr_allylic_oxid = Descriptors.fr_allylic_oxid(m)
        fr_amide = Descriptors.fr_amide(m)
        fr_aniline = Descriptors.fr_aniline(m)
        fr_benzene = Descriptors.fr_benzene(m)
        fr_bicyclic = Descriptors.fr_bicyclic(m)
        fr_epoxide = Descriptors.fr_epoxide(m)
        fr_ester = Descriptors.fr_ester(m)
        fr_ether = Descriptors.fr_ether(m)
        fr_ketone = Descriptors.fr_ketone(m)
        fr_ketone_Topliss = Descriptors.fr_ketone_Topliss(m)
        fr_lactam = Descriptors.fr_lactam(m)
        fr_lactone = Descriptors.fr_lactone(m)
        fr_para_hydroxylation = Descriptors.fr_para_hydroxylation(m)
        fr_phos_acid = Descriptors.fr_phos_acid(m)
        fr_phos_ester = Descriptors.fr_phos_ester(m)
        fr_piperzine = Descriptors.fr_piperzine(m)
        fr_quatN = Descriptors.fr_quatN(m)
        FractionCSP3 = Descriptors.FractionCSP3(m)
        HeavyAtomCount = Descriptors.HeavyAtomCount(m)
        NHOHCount = Descriptors.NHOHCount(m)
        NOCount = Descriptors.NOCount(m)
        NumAliphaticCarbocycles = Descriptors.NumAliphaticCarbocycles(m)
        NumAliphaticHeterocycles = Descriptors.NumAliphaticHeterocycles(m)
        NumAliphaticRings = Descriptors.NumAliphaticRings(m)
        NumAromaticCarbocycles = Descriptors.NumAromaticCarbocycles(m)
        NumAromaticHeterocycles = Descriptors.NumAromaticHeterocycles(m)
        NumAromaticRings = Descriptors.NumAromaticRings(m)
        NumHDonors = Descriptors.NumHDonors(m)
        NumHeteroatoms = Descriptors.NumHeteroatoms(m)
        NumRotatableBonds = Descriptors.NumRotatableBonds(m)
        NumSaturatedCarbocycles = Descriptors.NumSaturatedCarbocycles(m)
        NumSaturatedHeterocycles = Descriptors.NumSaturatedHeterocycles(m)
        NumSaturatedRings = Descriptors.NumSaturatedRings(m)

        # 组织特征字典
        features = {
            'EState_VSA1': EState_VSA1,
            'EState_VSA2': EState_VSA2,
            'EState_VSA4': EState_VSA4,
            'EState_VSA5': EState_VSA5,
            'EState_VSA6': EState_VSA6,
            'EState_VSA7': EState_VSA7,
            'EState_VSA8': EState_VSA8,
            'EState_VSA9': EState_VSA9,
            'EState_VSA10': EState_VSA10,
            'VSA_EState1': VSA_EState1,
            'VSA_EState2': VSA_EState2,
            'VSA_EState3': VSA_EState3,
            'VSA_EState5': VSA_EState5,
            'VSA_EState6': VSA_EState6,
            'VSA_EState8': VSA_EState8,
            'VSA_EState9': VSA_EState9,
            'QED': QED,
            'Chi0': Chi0,
            'Chi0n': Chi0n,
            'Chi0v': Chi0v,
            'Chi1': Chi1,
            'Chi1n': Chi1n,
            'Chi1v': Chi1v,
            'Chi2n': Chi2n,
            'Chi3n': Chi3n,
            'Chi3v': Chi3v,
            'Chi4n': Chi4n,
            'Chi4v': Chi4v,
            'HallKierAlpha': HallKierAlpha,
            'Kappa1': Kappa1,
            'Kappa2': Kappa2,
            'MinAbsPartialCharge': MinAbsPartialCharge,
            'FpDensityMorgan2': FpDensityMorgan2,
            'FpDensityMorgan3': FpDensityMorgan3,
            'FpDensityMorgan1': FpDensityMorgan1,
            'HeavyAtomMolWt': HeavyAtomMolWt,
            'ExactMolWt': ExactMolWt,
            'MolWt': MolWt,
            'NumValenceElectrons': NumValenceElectrons,
            'MaxPartialCharge': MaxPartialCharge,
            'MolMR': MolMR,
            'LabuteASA': LabuteASA,
            'PEOE_VSA1': PEOE_VSA1,
            'PEOE_VSA2': PEOE_VSA2,
            'PEOE_VSA3': PEOE_VSA3,
            'PEOE_VSA9': PEOE_VSA9,
            'PEOE_VSA10': PEOE_VSA10,
            'PEOE_VSA11': PEOE_VSA11,
            'PEOE_VSA13': PEOE_VSA13,
            'PEOE_VSA14': PEOE_VSA14,
            'SMR_VSA1': SMR_VSA1,
            'SMR_VSA2': SMR_VSA2,
            'SMR_VSA3': SMR_VSA3,
            'SMR_VSA4': SMR_VSA4,
            'SMR_VSA5': SMR_VSA5,
            'SMR_VSA6': SMR_VSA6,
            'SMR_VSA7': SMR_VSA7,
            'SMR_VSA10': SMR_VSA10,
            'SlogP_VSA2': SlogP_VSA2,
            'SlogP_VSA3': SlogP_VSA3,
            'SlogP_VSA4': SlogP_VSA4,
            'SlogP_VSA5': SlogP_VSA5,
            'SlogP_VSA6': SlogP_VSA6,
            'SlogP_VSA8': SlogP_VSA8,
            'TPSA': TPSA,
            'MaxAbsEStateIndex': MaxAbsEStateIndex,
            'MaxEStateIndex': MaxEStateIndex,
            'MinEStateIndex': MinEStateIndex,
            'fr_Al_OH': fr_Al_OH,
            'fr_Al_OH_noTert': fr_Al_OH_noTert,
            'fr_ArN': fr_ArN,
            'fr_Ar_N': fr_Ar_N,
            'fr_C_O': fr_C_O,
            'fr_C_O_noCOO': fr_C_O_noCOO,
            'fr_NH0': fr_NH0,
            'fr_Ndealkylation1': fr_Ndealkylation1,
            'fr_alkyl_halide': fr_alkyl_halide,
            'fr_allylic_oxid': fr_allylic_oxid,
            'fr_amide': fr_amide,
            'fr_aniline': fr_aniline,
            'fr_benzene': fr_benzene,
            'fr_bicyclic': fr_bicyclic,
            'fr_epoxide': fr_epoxide,
            'fr_ester': fr_ester,
            'fr_ether': fr_ether,
            'fr_ketone': fr_ketone,
            'fr_ketone_Topliss': fr_ketone_Topliss,
            'fr_lactam': fr_lactam,
            'fr_lactone': fr_lactone,
            'fr_para_hydroxylation': fr_para_hydroxylation,
            'fr_phos_acid': fr_phos_acid,
            'fr_phos_ester': fr_phos_ester,
            'fr_piperzine': fr_piperzine,
            'fr_quatN': fr_quatN,
            'FractionCSP3': FractionCSP3,
            'HeavyAtomCount': HeavyAtomCount,
            'NHOHCount': NHOHCount,
            'NOCount': NOCount,
            'NumAliphaticCarbocycles': NumAliphaticCarbocycles,
            'NumAliphaticHeterocycles': NumAliphaticHeterocycles,
            'NumAliphaticRings': NumAliphaticRings,
            'NumAromaticCarbocycles': NumAromaticCarbocycles,
            'NumAromaticHeterocycles': NumAromaticHeterocycles,
            'NumAromaticRings': NumAromaticRings,
            'NumHDonors': NumHDonors,
            'NumHeteroatoms': NumHeteroatoms,
            'NumRotatableBonds': NumRotatableBonds,
            'NumSaturatedCarbocycles': NumSaturatedCarbocycles,
            'NumSaturatedHeterocycles': NumSaturatedHeterocycles,
            'NumSaturatedRings': NumSaturatedRings
        }

    except Exception as e:
        print(f'特征化错误: {str(e)}')
        return None

    return features

# In[20]:

def featurize_two_class(linker):
    """二分类模型特征化函数"""
    try:
        m = Chem.MolFromSmiles(linker)
        if m is None:
            print(f"警告：无法解析SMILES: {linker}")
            return None
        
        # 计算描述符
        EState_VSA1 = Descriptors.EState_VSA1(m)
        EState_VSA2 = Descriptors.EState_VSA2(m)
        EState_VSA3 = Descriptors.EState_VSA3(m)
        EState_VSA4 = Descriptors.EState_VSA4(m)
        EState_VSA5 = Descriptors.EState_VSA5(m)
        EState_VSA6 = Descriptors.EState_VSA6(m)
        EState_VSA7 = Descriptors.EState_VSA7(m)
        EState_VSA8 = Descriptors.EState_VSA8(m)
        EState_VSA9 = Descriptors.EState_VSA9(m)
        EState_VSA10 = Descriptors.EState_VSA10(m)
        VSA_EState1 = Descriptors.VSA_EState1(m)
        VSA_EState2 = Descriptors.VSA_EState2(m)
        VSA_EState3 = Descriptors.VSA_EState3(m)
        VSA_EState5 = Descriptors.VSA_EState5(m)
        VSA_EState7 = Descriptors.VSA_EState7(m)
        VSA_EState8 = Descriptors.VSA_EState8(m)
        VSA_EState9 = Descriptors.VSA_EState9(m)
        VSA_EState10 = Descriptors.VSA_EState10(m)
        QED = Descriptors.qed(m)
        BertzCT = Descriptors.BertzCT(m)
        Chi0 = Descriptors.Chi0(m)
        Chi1 = Descriptors.Chi1(m)
        Chi3n = Descriptors.Chi3n(m)
        Chi4n = Descriptors.Chi4n(m)
        Chi4v = Descriptors.Chi4v(m)
        HallKierAlpha = Descriptors.HallKierAlpha(m)
        MinAbsPartialCharge = Descriptors.MinAbsPartialCharge(m)
        HeavyAtomMolWt = Descriptors.HeavyAtomMolWt(m)
        MaxAbsPartialCharge = Descriptors.MaxAbsPartialCharge(m)
        MinPartialCharge = Descriptors.MinPartialCharge(m)
        ExactMolWt = Descriptors.ExactMolWt(m)
        MolWt = Descriptors.MolWt(m)
        MaxPartialCharge = Descriptors.MaxPartialCharge(m)
        LabuteASA = Descriptors.LabuteASA(m)
        PEOE_VSA2 = Descriptors.PEOE_VSA2(m)
        PEOE_VSA3 = Descriptors.PEOE_VSA3(m)
        PEOE_VSA6 = Descriptors.PEOE_VSA6(m)
        PEOE_VSA7 = Descriptors.PEOE_VSA7(m)
        PEOE_VSA9 = Descriptors.PEOE_VSA9(m)
        PEOE_VSA10 = Descriptors.PEOE_VSA10(m)
        PEOE_VSA12 = Descriptors.PEOE_VSA12(m)
        PEOE_VSA13 = Descriptors.PEOE_VSA13(m)
        PEOE_VSA14 = Descriptors.PEOE_VSA14(m)
        SMR_VSA1 = Descriptors.SMR_VSA1(m)
        SMR_VSA2 = Descriptors.SMR_VSA2(m)
        SMR_VSA3 = Descriptors.SMR_VSA3(m)
        SMR_VSA5 = Descriptors.SMR_VSA5(m)
        SMR_VSA6 = Descriptors.SMR_VSA6(m)
        SMR_VSA7 = Descriptors.SMR_VSA7(m)
        SMR_VSA9 = Descriptors.SMR_VSA9(m)
        SMR_VSA10 = Descriptors.SMR_VSA10(m)
        SlogP_VSA1 = Descriptors.SlogP_VSA1(m)
        SlogP_VSA2 = Descriptors.SlogP_VSA2(m)
        SlogP_VSA3 = Descriptors.SlogP_VSA3(m)
        SlogP_VSA5 = Descriptors.SlogP_VSA5(m)
        SlogP_VSA6 = Descriptors.SlogP_VSA6(m)
        SlogP_VSA8 = Descriptors.SlogP_VSA8(m)
        SlogP_VSA10 = Descriptors.SlogP_VSA10(m)
        SlogP_VSA12 = Descriptors.SlogP_VSA12(m)
        TPSA = Descriptors.TPSA(m)
        MaxAbsEStateIndex = Descriptors.MaxAbsEStateIndex(m)
        MaxEStateIndex = Descriptors.MaxEStateIndex(m)
        MinEStateIndex = Descriptors.MinEStateIndex(m)
        MinAbsEStateIndex = Descriptors.MinAbsEStateIndex(m)
        fr_Al_COO = Descriptors.fr_Al_COO(m)
        fr_ArN = Descriptors.fr_ArN(m)
        fr_Ar_N = Descriptors.fr_Ar_N(m)
        fr_Ar_NH = Descriptors.fr_Ar_NH(m)
        fr_COO = Descriptors.fr_COO(m)
        fr_COO2 = Descriptors.fr_COO2(m)
        fr_C_O = Descriptors.fr_C_O(m)
        fr_C_O_noCOO = Descriptors.fr_C_O_noCOO(m)
        fr_NH0 = Descriptors.fr_NH0(m)
        fr_NH1 = Descriptors.fr_NH1(m)
        fr_Ndealkylation1 = Descriptors.fr_Ndealkylation1(m)
        fr_Ndealkylation2 = Descriptors.fr_Ndealkylation2(m)
        fr_Nhpyrrole = Descriptors.fr_Nhpyrrole(m)
        fr_amide = Descriptors.fr_amide(m)
        fr_aniline = Descriptors.fr_aniline(m)
        fr_benzene = Descriptors.fr_benzene(m)
        fr_ether = Descriptors.fr_ether(m)
        fr_halogen = Descriptors.fr_halogen(m)
        fr_hdrzone = Descriptors.fr_hdrzone(m)
        fr_imide = Descriptors.fr_imide(m)
        fr_morpholine = Descriptors.fr_morpholine(m)
        fr_nitro = Descriptors.fr_nitro(m)
        fr_nitro_arom = Descriptors.fr_nitro_arom(m)
        fr_nitro_arom_nonortho = Descriptors.fr_nitro_arom_nonortho(m)
        fr_para_hydroxylation = Descriptors.fr_para_hydroxylation(m)
        fr_piperdine = Descriptors.fr_piperdine(m)
        fr_priamide = Descriptors.fr_priamide(m)
        fr_quatN = Descriptors.fr_quatN(m)
        fr_sulfonamd = Descriptors.fr_sulfonamd(m)
        fr_urea = Descriptors.fr_urea(m)
        FractionCSP3 = Descriptors.FractionCSP3(m)
        HeavyAtomCount = Descriptors.HeavyAtomCount(m)
        NOCount = Descriptors.NOCount(m)
        NumAliphaticCarbocycles = Descriptors.NumAliphaticCarbocycles(m)
        NumAliphaticHeterocycles = Descriptors.NumAliphaticHeterocycles(m)
        NumAliphaticRings = Descriptors.NumAliphaticRings(m)
        NumAromaticCarbocycles = Descriptors.NumAromaticCarbocycles(m)
        NumAromaticHeterocycles = Descriptors.NumAromaticHeterocycles(m)
        NumAromaticRings = Descriptors.NumAromaticRings(m)
        NumHDonors = Descriptors.NumHDonors(m)
        NumHeteroatoms = Descriptors.NumHeteroatoms(m)
        NumRotatableBonds = Descriptors.NumRotatableBonds(m)
        NumSaturatedCarbocycles = Descriptors.NumSaturatedCarbocycles(m)
        NumSaturatedHeterocycles = Descriptors.NumSaturatedHeterocycles(m)
        NumSaturatedRings = Descriptors.NumSaturatedRings(m)
        RingCount = Descriptors.RingCount(m)

        # 组织特征字典
        features = {
            'EState_VSA1': EState_VSA1,
            'EState_VSA2': EState_VSA2,
            'EState_VSA3': EState_VSA3,
            'EState_VSA4': EState_VSA4,
            'EState_VSA5': EState_VSA5,
            'EState_VSA6': EState_VSA6,
            'EState_VSA7': EState_VSA7,
            'EState_VSA8': EState_VSA8,
            'EState_VSA9': EState_VSA9,
            'EState_VSA10': EState_VSA10,
            'VSA_EState1': VSA_EState1,
            'VSA_EState2': VSA_EState2,
            'VSA_EState3': VSA_EState3,
            'VSA_EState5': VSA_EState5,
            'VSA_EState7': VSA_EState7,
            'VSA_EState8': VSA_EState8,
            'VSA_EState9': VSA_EState9,
            'VSA_EState10': VSA_EState10,
            'QED': QED,
            'BertzCT': BertzCT,
            'Chi0': Chi0,
            'Chi1': Chi1,
            'Chi3n': Chi3n,
            'Chi4n': Chi4n,
            'Chi4v': Chi4v,
            'HallKierAlpha': HallKierAlpha,
            'MinAbsPartialCharge': MinAbsPartialCharge,
            'HeavyAtomMolWt': HeavyAtomMolWt,
            'MaxAbsPartialCharge': MaxAbsPartialCharge,
            'MinPartialCharge': MinPartialCharge,
            'ExactMolWt': ExactMolWt,
            'MolWt': MolWt,
            'MaxPartialCharge': MaxPartialCharge,
            'LabuteASA': LabuteASA,
            'PEOE_VSA2': PEOE_VSA2,
            'PEOE_VSA3': PEOE_VSA3,
            'PEOE_VSA6': PEOE_VSA6,
            'PEOE_VSA7': PEOE_VSA7,
            'PEOE_VSA9': PEOE_VSA9,
            'PEOE_VSA10': PEOE_VSA10,
            'PEOE_VSA12': PEOE_VSA12,
            'PEOE_VSA13': PEOE_VSA13,
            'PEOE_VSA14': PEOE_VSA14,
            'SMR_VSA1': SMR_VSA1,
            'SMR_VSA2': SMR_VSA2,
            'SMR_VSA3': SMR_VSA3,
            'SMR_VSA5': SMR_VSA5,
            'SMR_VSA6': SMR_VSA6,
            'SMR_VSA7': SMR_VSA7,
            'SMR_VSA9': SMR_VSA9,
            'SMR_VSA10': SMR_VSA10,
            'SlogP_VSA1': SlogP_VSA1,
            'SlogP_VSA2': SlogP_VSA2,
            'SlogP_VSA3': SlogP_VSA3,
            'SlogP_VSA5': SlogP_VSA5,
            'SlogP_VSA6': SlogP_VSA6,
            'SlogP_VSA8': SlogP_VSA8,
            'SlogP_VSA10': SlogP_VSA10,
            'SlogP_VSA12': SlogP_VSA12,
            'TPSA': TPSA,
            'MaxAbsEStateIndex': MaxAbsEStateIndex,
            'MaxEStateIndex': MaxEStateIndex,
            'MinEStateIndex': MinEStateIndex,
            'MinAbsEStateIndex': MinAbsEStateIndex,
            'fr_Al_COO': fr_Al_COO,
            'fr_ArN': fr_ArN,
            'fr_Ar_N': fr_Ar_N,
            'fr_Ar_NH': fr_Ar_NH,
            'fr_COO': fr_COO,
            'fr_COO2': fr_COO2,
            'fr_C_O': fr_C_O,
            'fr_C_O_noCOO': fr_C_O_noCOO,
            'fr_NH0': fr_NH0,
            'fr_NH1': fr_NH1,
            'fr_Ndealkylation1': fr_Ndealkylation1,
            'fr_Ndealkylation2': fr_Ndealkylation2,
            'fr_Nhpyrrole': fr_Nhpyrrole,
            'fr_amide': fr_amide,
            'fr_aniline': fr_aniline,
            'fr_benzene': fr_benzene,
            'fr_ether': fr_ether,
            'fr_halogen': fr_halogen,
            'fr_hdrzone': fr_hdrzone,
            'fr_imide': fr_imide,
            'fr_morpholine': fr_morpholine,
            'fr_nitro': fr_nitro,
            'fr_nitro_arom': fr_nitro_arom,
            'fr_nitro_arom_nonortho': fr_nitro_arom_nonortho,
            'fr_para_hydroxylation': fr_para_hydroxylation,
            'fr_piperdine': fr_piperdine,
            'fr_priamide': fr_priamide,
            'fr_quatN': fr_quatN,
            'fr_sulfonamd': fr_sulfonamd,
            'fr_urea': fr_urea,
            'FractionCSP3': FractionCSP3,
            'HeavyAtomCount': HeavyAtomCount,
            'NOCount': NOCount,
            'NumAliphaticCarbocycles': NumAliphaticCarbocycles,
            'NumAliphaticHeterocycles': NumAliphaticHeterocycles,
            'NumAliphaticRings': NumAliphaticRings,
            'NumAromaticCarbocycles': NumAromaticCarbocycles,
            'NumAromaticHeterocycles': NumAromaticHeterocycles,
            'NumAromaticRings': NumAromaticRings,
            'NumHDonors': NumHDonors,
            'NumHeteroatoms': NumHeteroatoms,
            'NumRotatableBonds': NumRotatableBonds,
            'NumSaturatedCarbocycles': NumSaturatedCarbocycles,
            'NumSaturatedHeterocycles': NumSaturatedHeterocycles,
            'NumSaturatedRings': NumSaturatedRings,
            'RingCount': RingCount
        }

    except Exception as e:
        print(f'特征化错误: {str(e)}')
        return None

    return features

# In[21]:

def predict_with_shap(molecule_smiles, molecule_name=""):
    """
    使用SHAP进行预测和解释
    """
    print(f"\n{'='*80}")
    print(f"分析分子: {molecule_name}")
    print(f"SMILES: {molecule_smiles}")
    print('='*80)
    
    # 1. 特征化
    print("1. 特征化...")
    features_three = featurize_three_class(molecule_smiles)
    features_two = featurize_two_class(molecule_smiles)
    
    if features_three is None or features_two is None:
        print("特征化失败，请检查SMILES字符串")
        return None, None
    
    X_three = pd.DataFrame([features_three], columns=features_three.keys())
    X_two = pd.DataFrame([features_two], columns=features_two.keys())
    
    # 2. 预测
    print("2. 预测...")
    prediction_three = model_three_class.predict(X_three)
    prediction_two = None
    
    # 获取类别名称
    def get_class_name(pred, is_two_class=False):
        if is_two_class:
            return "更毒" if pred == -1 else "较不毒"
        else:
            if pred == -1:
                return "致命"
            elif pred == 0:
                return "有毒"
            else:
                return "安全"
    
    print(f"三分类预测结果: {prediction_three} ({get_class_name(prediction_three)})")
    
    # 3. SHAP分析
    print("\n3. SHAP分析...")
    
    # 计算SHAP值
    shap_values_three = explainer_three_class.shap_values(X_three)
    
    # 如果是多分类，选择对应类别的SHAP值
    if isinstance(shap_values_three, list):
        # 多分类情况
        class_idx = { -1: 0, 0: 1, 1: 2 }  # 假设类别映射
        shap_vals = shap_values_three[class_idx[prediction_three]]
    else:
        # 二分类情况
        shap_vals = shap_values_three
    
    # 4. 可视化
    print("\n4. 可视化结果...")
    
    # 创建子图
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'分子: {molecule_name} - 三分类预测: {get_class_name(prediction_three)}', fontsize=16)
    
    # 4.1 SHAP力图示
    shap.force_plot(
        explainer_three_class.expected_value[class_idx[prediction_three]] if isinstance(explainer_three_class.expected_value, list) else explainer_three_class.expected_value,
        shap_vals,
        X_three.iloc[0],
        matplotlib=True,
        show=False,
        fig=axes[0, 0]
    )
    axes[0, 0].set_title('SHAP力图示', fontsize=14)
    
    # 4.2 特征重要性条形图
    shap.summary_plot(shap_vals, X_three, plot_type="bar", show=False)
    axes[0, 1].set_title('特征重要性排序', fontsize=14)
    
    # 4.3 SHAP摘要图
    if isinstance(shap_values_three, list):
        shap.summary_plot(shap_values_three, X_three, show=False)
    else:
        shap.summary_plot(shap_vals, X_three, show=False)
    axes[1, 0].set_title('SHAP摘要图', fontsize=14)
    
    # 4.4 决策图
    shap.decision_plot(
        explainer_three_class.expected_value[class_idx[prediction_three]] if isinstance(explainer_three_class.expected_value, list) else explainer_three_class.expected_value,
        shap_vals,
        X_three.iloc[0],
        show=False,
        feature_names=list(X_three.columns)
    )
    axes[1, 1].set_title('决策图', fontsize=14)
    
    plt.tight_layout()
    plt.show()
    
    # 5. 详细特征解释
    print("\n5. 详细特征解释:")
    print("-"*80)
    
    # 创建特征贡献度DataFrame
    feature_contributions = pd.DataFrame({
        '特征': X_three.columns,
        '特征值': X_three.iloc[0].values,
        'SHAP值': shap_vals[0] if len(shap_vals.shape) > 1 else shap_vals
    })
    
    # 计算绝对贡献度
    feature_contributions['绝对贡献度'] = abs(feature_contributions['SHAP值'])
    feature_contributions = feature_contributions.sort_values('绝对贡献度', ascending=False)
    
    # 显示前10个最重要的特征
    print("前10个最重要的特征及其贡献:")
    for i, row in feature_contributions.head(10).iterrows():
        direction = "增加毒性概率" if row['SHAP值'] > 0 else "减少毒性概率"
        print(f"{row['特征']:30s} | 值: {row['特征值']:8.4f} | "
              f"贡献: {row['SHAP值']:8.4f} | {direction}")
    
    # 6. 如果需要二分类预测
    if prediction_three == 0:
        print("\n" + "="*80)
        print("进行二分类细化分析...")
        
        prediction_two = model_two_class.predict(X_two)
        print(f"二分类预测结果: {prediction_two} ({get_class_name(prediction_two, is_two_class=True)})")
        
        # 二分类SHAP分析
        shap_values_two = explainer_two_class.shap_values(X_two)
        
        # 二分类可视化
        fig2, axes2 = plt.subplots(1, 2, figsize=(14, 6))
        fig2.suptitle(f'二分类分析 - 预测: {get_class_name(prediction_two, is_two_class=True)}', fontsize=14)
        
        # 力图示
        shap.force_plot(
            explainer_two_class.expected_value,
            shap_values_two[0],
            X_two.iloc[0],
            matplotlib=True,
            show=False,
            fig=axes2
        )
        axes2[0].set_title('SHAP力图示')
        
        # 特征重要性
        shap.summary_plot(shap_values_two, X_two, plot_type="bar", show=False)
        axes2[1].set_title('特征重要性排序')
        
        plt.tight_layout()
        plt.show()
        
        # 二分类特征解释
        feature_contributions_two = pd.DataFrame({
            '特征': X_two.columns,
            '特征值': X_two.iloc[0].values,
            'SHAP值': shap_values_two
        })
        feature_contributions_two['绝对贡献度'] = abs(feature_contributions_two['SHAP值'])
        feature_contributions_two = feature_contributions_two.sort_values('绝对贡献度', ascending=False)
        
        print("\n二分类前10个最重要的特征:")
        for i, row in feature_contributions_two.head(10).iterrows():
            direction = "增加毒性程度" if row['SHAP值'] > 0 else "减少毒性程度"
            print(f"{row['特征']:30s} | 值: {row['特征值']:8.4f} | "
                  f"贡献: {row['SHAP值']:8.4f} | {direction}")
    
    return prediction_three, prediction_two

# In[22]:

# 测试分子
test_molecules = [
    ("Δ9-THC", 'CCCCCC1=CC2=C(C3C=C(CCC3C(O2)(C)C)C)C(=C1C(=O)O)O'),
    ("芬太尼", 'CCC(=O)N(C1CCN(CC1)CCC2=CC=CC=C2)C3=CC=CC=C3'),
    ("TBAPy", 'C1=CC(=CC=C1C2=CC(=C3C=CC4=C(C=C(C5=C4C3=C2C=C5)C6=CC=C(C=C6)C(=O)O)C7=CC=C(C=C7)C(=O)O)C8=CC=C(C=C8)C(=O)O)C(=O)O'),
    ("MIM", 'CC1=NC=CN1'),
    ("阿霉素", 'CC1C(C(CC(O1)OC2CC(CC3=C2C(=C4C(=C3O)C(=O)C5=C(C4=O)C(=CC=C5)OC)O)(C(=O)CO)O)N)O'),
    ("紫杉醇", 'CC1=C2C(C(=O)C3(C(CC4C(C3C(C(C2(C)C)(CC1OC(=O)C(C(C5=CC=CC=C5)NC(=O)C6=CC=CC=C6)O)O)OC(=O)C7=CC=CC=C7)(CO4)OC(=O)C)O)C)OC(=O)C'),
    ("姜黄素", 'COC1=C(C=CC(=C1)C=CC(=O)CC(=O)C=CC2=CC(=C(C=C2)O)OC)O'),
    ("布洛芬", 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O'),
    ("咖啡因", 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C'),
    ("卟啉", 'C1=CC(=CC=C1C2=C3C=CC(=C(C4=CC=C(N4)C(=C5C=CC(=N5)C(=C6C=CC2=N6)C7=CC=C(C=C7)C(=O)O)C8=CC=C(C=C8)C(=O)O)C9=CC=C(C=C9)C(=O)O)N3)C(=O)O'),
    ("MIM-MO", 'O=Cc1ncc[nH]1'),
    ("PCN-128", 'C1=CC(=CC=C1C2=CC=C(C=C2)C(=O)O)C(=C(C3=CC=C(C=C3)C4=CC=C(C=C4)C(=O)O)C5=CC=C(C=C5)C6=CC=C(C=C6)C(=O)O)C7=CC=C(C=C7)C8=CC=C(C=C8)C(=O)O'),
    ("用户分子", 'O=C(O)c8c(F)c(F)c(c4cc(c1c(F)c(F)c(C(=O)O)c(F)c1F)c5ccc7c(c2c(F)c(F)c(C(=O)O)c(F)c2F)cc(c3c(F)c(F)c(C(=O)O)c(F)c3F)c6ccc4c5c67)c(F)c8F')
]

# 对每个测试分子进行预测和SHAP分析
for name, smiles in test_molecules[:3]:  # 先测试前3个分子
    pred_three, pred_two = predict_with_shap(smiles, name)

# In[23]:

# 全局SHAP分析（可选）
def global_shap_analysis():
    """全局SHAP分析"""
    print("进行全局SHAP分析...")
    
    # 三分类模型全局分析
    print("\n1. 三分类模型全局特征重要性:")
    fig1, axes1 = plt.subplots(1, 2, figsize=(14, 6))
    
    # 全局特征重要性
    shap.summary_plot(shap_values_three_train, X_three, show=False, plot_type="bar")
    axes1[0].set_title('三分类全局特征重要性')
    
    # 全局SHAP摘要图
    shap.summary_plot(shap_values_three_train, X_three, show=False)
    axes1[1].set_title('三分类全局SHAP摘要图')
    
    plt.tight_layout()
    plt.show()
    
    # 二分类模型全局分析
    print("\n2. 二分类模型全局特征重要性:")
    fig2, axes2 = plt.subplots(1, 2, figsize=(14, 6))
    
    shap.summary_plot(shap_values_two_train, X_two, show=False, plot_type="bar")
    axes2[0].set_title('二分类全局特征重要性')
    
    shap.summary_plot(shap_values_two_train, X_two, show=False)
    axes2[1].set_title('二分类全局SHAP摘要图')
    
    plt.tight_layout()
    plt.show()

# 运行全局分析（可选）
# global_shap_analysis()

# In[24]:

# 交互式预测函数
def interactive_prediction():
    """交互式预测函数"""
    print("="*80)
    print("MOF连接体毒性预测系统")
    print("="*80)
    
    while True:
        print("\n请输入MOF连接体的SMILES字符串（输入'quit'退出）：")
        smiles = input("SMILES: ").strip()
        
        if smiles.lower() == 'quit':
            print("感谢使用！")
            break
        
        if not smiles:
            print("请输入有效的SMILES字符串")
            continue
        
        # 进行预测和SHAP分析
        try:
            pred_three, pred_two = predict_with_shap(smiles, "用户输入分子")
            
            print("\n" + "="*80)
            print("预测总结:")
            print(f"三分类结果: {pred_three} ({get_class_name(pred_three)})")
            if pred_three == 0:
                print(f"二分类细化: {pred_two} ({get_class_name(pred_two, is_two_class=True)})")
            print("="*80)
            
        except Exception as e:
            print(f"预测过程中出现错误: {str(e)}")
            print("请检查SMILES字符串是否正确")

# 运行交互式预测
# interactive_prediction()

# In[25]:

# 批量预测函数
def batch_prediction(smiles_list, names=None):
    """批量预测函数"""
    results = []
    
    for i, smiles in enumerate(smiles_list):
        name = names[i] if names and i < len(names) else f"分子_{i+1}"
        print(f"\n处理第 {i+1}/{len(smiles_list)} 个分子: {name}")
        
        try:
            pred_three, pred_two = predict_with_shap(smiles, name)
            results.append({
                'name': name,
                'smiles': smiles,
                'pred_three': pred_three,
                'pred_three_name': get_class_name(pred_three),
                'pred_two': pred_two,
                'pred_two_name': get_class_name(pred_two, is_two_class=True) if pred_two is not None else None
            })
        except Exception as e:
            print(f"处理分子 {name} 时出错: {str(e)}")
            results.append({
                'name': name,
                'smiles': smiles,
                'error': str(e)
            })
    
    # 保存结果
    results_df = pd.DataFrame(results)
    results_df.to_csv('mof_toxicity_predictions.csv', index=False, encoding='utf-8-sig')
    print(f"\n预测结果已保存到 'mof_toxicity_predictions.csv'")
    
    return results_df

# 批量预测示例
# batch_smiles = [smiles for _, smiles in test_molecules]
# batch_names = [name for name, _ in test_molecules]
# results = batch_prediction(batch_smiles, batch_names)

# In[ ]:
