---
theme: academic
cover-title: 基于深度学习的工业设备故障预测方法研究
subtitle: 面向多传感器时序数据的 LSTM-Attention 模型设计与验证
doc-authors: 张明 · 李华 · 王芳
doc-institution: 清华大学 自动化系
doc-date: 2026.06
document-title: 工业设备故障预测方法研究
lang: zh-CN
---

::: abstract
## 摘要

随着工业物联网（IIoT）的普及，设备运行过程中产生的高频多变量时序数据为预测性维护提供了
新的技术基础。然而，传统基于固定阈值的告警机制难以适应复杂工况下的非线性退化模式，
导致误报率高、漏报严重。本文提出一种融合长短期记忆网络（LSTM）与注意力机制的故障
预测框架，对多传感器时序数据进行联合建模，实现对未来 $T$ 步内设备异常状态的提前
识别。

在 NASA C-MAPSS 公开数据集与某大型制造企业自建 EAM 数据集上，本文方法在 F1 分数上
分别达到 0.87 与 0.83，相比 XGBoost 基线提升 12.4% 与 9.7%；误报率较传统阈值方案
降低 34%。消融实验表明，注意力模块对长序列依赖建模贡献显著，移除后 F1 下降 6.2 个
百分点。此外，本文讨论了模型可解释性、边缘部署与数据隐私等工程化问题，为工业场景
落地提供参考。

**关键词：** 故障预测 · 深度学习 · LSTM · 注意力机制 · 时序分析 · 预测性维护
:::

## 引言 {.section-header label="1"}

### 研究背景

设备预测性维护（Predictive Maintenance, PdM）是工业 4.0 与智能制造的核心能力之一。
据统计，非计划停机导致的产能损失可占制造企业年营收的 5%–20%。早期故障预警能够在
设备完全失效前留出检修窗口，从而显著降低维护成本与安全事故风险。

传统 PdM 方案多依赖专家经验设定阈值规则，例如当振动幅值超过 $A_{\max}$ 或温度持续
高于 $T_{\mathrm{hi}}$ 时触发告警。这类方法实现简单，但在以下场景表现不佳：

- 工况切换频繁，正常波动范围随负载变化；
- 多传感器之间存在耦合关系，单变量阈值无法捕捉联合异常；
- 退化过程缓慢，固定窗口统计量对早期微弱信号不敏感。

近年来，深度学习在时序建模领域取得显著进展。循环神经网络及其变体 LSTM、GRU 能够
建模长程依赖；注意力机制可自适应地聚焦关键时间步；Transformer 架构则在部分公开
基准上刷新了最优记录。然而，工业现场对模型的可解释性、推理延迟与数据合规性提出了
更高要求，学术模型与工程落地之间仍存在差距。

### 研究问题与贡献

本文聚焦以下三个问题：（1）如何在标注样本有限的情况下，利用无监督预训练提升故障
预测性能；（2）注意力权重能否为运维人员提供可理解的异常定位线索；（3）模型在
边缘网关上的推理开销是否满足实时性约束。

主要贡献如下：

1. 提出 LSTM-Attention 编码器-解码器架构，对多变量传感器序列进行端到端故障预测；
2. 设计滑动窗口标签策略与类别不平衡损失函数，适配工业数据的长尾分布；
3. 在公开与私有数据集上系统对比 6 种基线方法，并给出消融与可解释性分析；
4. 讨论联邦学习与知识蒸馏在跨厂区部署中的可行性。

行内公式示例：设备健康指数定义为 $H(t) = \sum_{i=1}^{n} w_i x_i(t)$，其中 $x_i(t)$
为第 $i$ 个传感器在时刻 $t$ 的归一化读数，$w_i$ 为可学习或专家给定的权重。

## 相关工作 {.section-header label="2"}

### 传统统计与机器学习

早期故障诊断方法包括主成分分析（PCA）、偏最小二乘（PLS）与自回归滑动平均（ARIMA）
等。这类方法假设数据近似线性或平稳，对非线性退化过程的表达能力有限。支持向量机
（SVM）与随机森林（RF）在特征工程充分的前提下，于中小规模数据集上仍具竞争力。

梯度提升树（XGBoost、LightGBM）因训练效率高、可解释性较好，在工业竞赛与 Kaggle
相关赛道中广泛使用。其局限在于需人工构造滞后特征与统计量，且对长序列的直接建模
能力较弱。

### 深度学习时序模型

Hochreiter 与 Schmidhuber 提出的 LSTM 通过门控机制缓解梯度消失，成为时序预测
的默认选择之一。Vaswani 等人提出的 Transformer 以自注意力替代循环结构，在 NLP
与部分时序基准上表现优异，但对小样本工业数据的过拟合风险需通过正则化与预训练
加以控制。

在设备健康管理（PHM）领域，Zheng 等人将 CNN-LSTM 用于剩余寿命（RUL）预测；
Li 等人引入图神经网络建模传感器拓扑。本文选择与 LSTM-Attention 路线，在模型
复杂度与可解释性之间取得平衡。

## 方法 {.section-header label="3"}

### 问题形式化

设多传感器观测序列为 $\mathbf{X} = \{ \mathbf{x}_1, \mathbf{x}_2, \ldots, \mathbf{x}_T \}$，
其中 $\mathbf{x}_t \in \mathbb{R}^d$ 为 $d$ 维特征向量。给定长度为 $L$ 的历史窗口
$\mathbf{X}_{t-L+1:t}$，预测未来 $H$ 步内是否发生故障：

$$
\hat{y}_t = f_\theta(\mathbf{X}_{t-L+1:t}) \in \{0, 1\}
$$

其中 $y_t=1$ 表示在 $(t, t+H]$ 内观测到故障事件。损失函数采用加权交叉熵：

$$
\mathcal{L} = -\frac{1}{N}\sum_{i=1}^{N} \left[ \alpha y_i \log \hat{y}_i + (1-y_i)\log(1-\hat{y}_i) \right]
$$

正样本权重 $\alpha$ 根据训练集正负比例设定，典型取值为 3–8。

### 模型架构

我们采用双向 LSTM 编码历史窗口，再通过注意力池化聚合隐状态，最后经全连接层输出
故障概率。核心预测公式为：

$$
\hat{y}_{t+1} = \sigma\left(\mathbf{W} \cdot \mathrm{Attention}(\mathbf{h}_t, \mathbf{h}_{t-1}, \ldots)\right)
$$

其中 $\mathbf{h}_t$ 为 LSTM 隐状态，$\sigma$ 为 sigmoid 函数，Attention 计算为：

$$
\alpha_k = \frac{\exp(\mathbf{v}^\top \tanh(\mathbf{W}_a \mathbf{h}_k))}{\sum_j \exp(\mathbf{v}^\top \tanh(\mathbf{W}_a \mathbf{h}_j))}, \quad
\mathbf{c} = \sum_k \alpha_k \mathbf{h}_k
$$

::: {.figure caption="Figure 1. LSTM-Attention 故障预测模型结构"}
模型由输入归一化层、双向 LSTM 编码器（2 层，隐维度 128）、注意力池化层、Dropout（$p=0.3$）
与全连接分类头组成。推理阶段输出故障概率及 Top-3 注意力时间步索引，供运维人员回溯。
:::

### 训练策略

- **数据划分：** 按时间顺序 70% / 15% / 15% 划分训练、验证、测试集，避免未来信息泄漏；
- **窗口长度：** $L \in \{32, 64, 128\}$ 网格搜索，默认 $L=64$；
- **优化器：** Adam，初始学习率 $10^{-3}$，余弦退火；
- **早停：** 验证集 F1 连续 10 epoch 无提升则停止训练。

::: {.figure caption="Figure 2. 滑动窗口标签构造示意"}
对每个时刻 $t$，若 $(t, t+H]$ 内存在故障记录则标为阳性；否则为阴性。窗口边界处
不足 $L$ 步的样本予以丢弃。
:::

## 实验 {.section-header label="4"}

### 数据集

| 数据集 | 样本数 | 特征维度 | 采样间隔 | 故障比例 |
| --- | --- | --- | --- | --- |
| C-MAPSS FD001 | 26,000 | 21 | 1 min | 4.2% |
| C-MAPSS FD004 | 61,200 | 21 | 1 min | 6.8% |
| 自建 EAM（脱敏） | 18,400 | 32 | 5 min | 3.1% |

C-MAPSS 为 NASA 发布的涡扇发动机退化仿真数据；EAM 数据集来自某流程工业集团 3 年
真实运维记录，经脱敏与重采样处理。所有连续特征经 Z-score 标准化，类别特征采用
目标编码。

### 基线方法

| 方法 | 类型 | 主要超参数 |
| --- | --- | --- |
| Threshold | 规则 | 3$\sigma$ 阈值 |
| PCA + Q-statistic | 统计 | 主成分数 10 |
| XGBoost | 集成 | 树深度 6，500 轮 |
| 1D-CNN | 深度学习 | 3 层卷积，核宽 3 |
| BiLSTM | 深度学习 | 隐维度 128，2 层 |
| **Ours (LSTM-Attn)** | 深度学习 | 见 §3.3 |

### 主实验结果

表 3 汇报各方法在测试集上的 Precision、Recall 与 F1。本文方法在两个 C-MAPSS 子集
与 EAM 数据集上均取得最优或次优 F1。

| 方法 | C-MAPSS FD001 F1 | C-MAPSS FD004 F1 | EAM F1 |
| --- | --- | --- | --- |
| Threshold | 0.52 | 0.48 | 0.41 |
| PCA + Q | 0.61 | 0.58 | 0.55 |
| XGBoost | 0.75 | 0.72 | 0.73 |
| 1D-CNN | 0.78 | 0.74 | 0.76 |
| BiLSTM | 0.81 | 0.78 | 0.79 |
| **LSTM-Attention** | **0.87** | **0.84** | **0.83** |

在 EAM 数据集上，本文方法将误报率从阈值方案的 28.6% 降至 18.9%，平均提前预警时间
为 52 小时（中位数 48 小时），满足企业「至少提前 2 天」的业务要求。

### 消融实验

| 配置 | F1 (FD001) | $\Delta$ |
| --- | --- | --- |
| 完整模型 | 0.87 | — |
| 移除注意力 | 0.81 | −6.2% |
| 单向 LSTM | 0.84 | −3.4% |
| 窗口 $L=32$ | 0.82 | −5.7% |
| 无类别权重 | 0.79 | −9.2% |

结果表明注意力模块与类别加权对性能贡献最大。窗口过短会损失长程退化信息。

::: {.figure caption="Figure 3. 注意力权重热力图（故障样本 #1847）"}
横轴为时间步，纵轴为传感器通道。故障发生前 12–18 步内，振动与温度通道权重显著升高，
与领域专家标注的异常时段一致。
:::

### 推理性能

在 NVIDIA Jetson Orin 边缘设备上，批量大小为 1 时单次推理延迟为 8.3 ms，满足 5 min
采样间隔下的实时要求。模型参数量 1.2M，INT8 量化后体积 1.8 MB，可部署于现有
工业网关。

## 讨论 {.section-header label="5"}

### 可解释性

注意力权重提供了「何时、哪些传感器」的线索，但不应等同于因果解释。未来可结合
SHAP 值与知识图谱中的设备-部件-故障模式关联，生成自然语言解释报告。

### 局限与威胁

（1）EAM 数据来自单一行业，跨域泛化需进一步验证；（2）极端罕见故障样本不足，
模型对长尾类别的召回仍有限；（3）传感器故障或通信中断会导致输入缺失，需与数据
质量模块联动。

### 工程落地建议

建议企业按「高价值设备优先、闭环反馈迭代」路径推进：首批选择 20–50 台关键设备
试点，将模型告警与工单系统打通，由运维人员标注误报/漏报，每季度重训练一次。

### 附录：符号说明

| 符号 | 含义 |
| --- | --- |
| $\mathbf{x}_t$ | 时刻 $t$ 的 $d$ 维传感器向量 |
| $L$ | 历史窗口长度（默认 64 步） |
| $H$ | 预测视野（默认 48 步，对应 4 小时 @5min 采样） |
| $\alpha_k$ | 第 $k$ 个时间步的注意力权重 |
| $\hat{y}_t$ | 故障概率估计值 |

上述符号在全文公式中保持一致。窗口长度 $L$ 与预测视野 $H$ 的选取需结合设备
退化时间常数与业务可接受的提前量综合确定：对于慢退化设备（如大型压缩机），
可适当增大 $H$；对于快变工况（如间歇式反应釜），应缩短 $L$ 以跟踪近期动态。

## 结论 {.section-header label="6"}

本文提出面向工业多传感器时序数据的 LSTM-Attention 故障预测方法，在公开与私有
数据集上验证了有效性。实验表明，深度序列模型结合注意力机制能够显著提升早期
故障识别能力，并在边缘设备上满足实时推理约束。未来工作将探索：（1）跨厂区
联邦学习框架；（2）与大型语言模型结合的可解释报告生成；（3）数字孪生驱动的
仿真数据增强。

## 参考文献

1. Hochreiter S., Schmidhuber J. Long Short-Term Memory. *Neural Computation*, 9(8):1735–1780, 1997.
2. Vaswani A., Shazeer N., Parmar N., et al. Attention Is All You Need. *NeurIPS*, 2017.
3. Saxena A., Goebel K., Simon D., Eklund N. Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation. *PHM*, 2008.
4. Chen T., Guestrin C. XGBoost: A Scalable Tree Boosting System. *KDD*, 2016.
5. Zheng S., Ristovski B., Farahat A., Gupta C. Long Short-Term Memory Network for Remaining Useful Life Estimation. *ICPHM*, 2017.
6. Li X., Ding Q., Sun J.-Q. Remaining Useful Life Estimation in Prognostics Using Deep Convolution Neural Networks. *Reliability Engineering & System Safety*, 2018.
7. Bahdanau D., Cho K., Bengio Y. Neural Machine Translation by Jointly Learning to Align and Translate. *ICLR*, 2015.
8. McMahan B., Moore E., Ramage D., et al. Communication-Efficient Learning of Deep Networks from Decentralized Data. *AISTATS*, 2017.
