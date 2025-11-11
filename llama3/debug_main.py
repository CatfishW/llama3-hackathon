import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from transformers import pipeline
import warnings
warnings.filterwarnings('ignore')

# 读取CSV文件
def load_data(filepath):
    try:
        df = pd.read_csv(filepath)
        print(f"数据加载成功，形状: {df.shape}")
        print(df.head())
        print(df.info())
        return df
    except Exception as e:
        print(f"加载数据时出错: {e}")
        return None

# 数据预处理
def preprocess_data(df):
    # 检查缺失值
    print("缺失值统计:")
    print(df.isnull().sum())
    
    # 删除缺失值
    df = df.dropna()
    
    # 处理异常数据
    # 检查label字段的分布
    print("label字段分布:")
    print(df['label'].value_counts())
    
    # 检查唯一标签值
    print("唯一标签值:", df['label'].unique())
    
    # 保证label是二分类
    if df['label'].nunique() != 2:
        print("警告: label字段不是二分类，将进行转换")
        # 重新编码label，确保是0和1
        le = LabelEncoder()
        df['label'] = le.fit_transform(df['label'])
    
    # 分离特征和标签
    X = df['message']
    y = df['label']
    
    return X, y

# 自定义数据集类
class TextClassificationDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts.iloc[idx])
        label = self.labels.iloc[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

# 主程序
def main():
    # 加载数据
    df = load_data("src/train_cleaned_updated.csv")
    if df is None:
        print("数据加载失败，程序退出")
        return
    
    # 数据预处理
    X, y = preprocess_data(df)
    
    # 划分训练集和验证集
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"训练集大小: {len(X_train)}")
    print(f"验证集大小: {len(X_val)}")
    
    # 使用中文模型
    model_name = "bert-base-chinese"
    
    # 初始化分词器
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # 创建数据集
    train_dataset = TextClassificationDataset(X_train, y_train, tokenizer)
    val_dataset = TextClassificationDataset(X_val, y_val, tokenizer)
    
    # 初始化模型
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2
    )
    
    # 训练参数
    training_args = TrainingArguments(
        output_dir='./results',
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        evaluation_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=500,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        greater_is_better=True,
    )
    
    # 训练器
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
    )
    
    # 开始训练
    print("开始训练模型...")
    trainer.train()
    
    # 评估模型
    print("评估模型...")
    eval_results = trainer.evaluate()
    print(f"验证集结果: {eval_results}")
    
    # 预测示例
    print("进行预测示例...")
    classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)
    
    # 从验证集中取几个样本进行预测
    sample_texts = X_val.iloc[:5].tolist()
    predictions = classifier(sample_texts)
    
    for i, (text, pred) in enumerate(zip(sample_texts, predictions)):
        print(f"样本 {i+1}: {text[:100]}...")
        print(f"预测结果: {pred}")
        print()

if __name__ == "__main__":
    main()