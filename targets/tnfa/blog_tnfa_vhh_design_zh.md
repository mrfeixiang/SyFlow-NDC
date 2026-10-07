# AI驱动的TNF-α纳米抗体设计：从计算到湿实验的全流程实战

**作者：SyFlow AIDD团队 | 日期：2026年10月6日**

---

## 一、竞赛背景

Anthropic联合Adaptyv Bio举办了2026年蛋白质设计大赛，提供超过100万美元的Claude API算力支持和100万美元以上的湿实验验证经费。本次TNF-α挑战赛（Challenge 02）要求参赛者设计能结合人TNF-α三聚体的全新纳米抗体（VHH），并需满足三个递进目标：

| 目标 | 描述 | 难度 |
|------|------|------|
| 1. 结合亲和力 | 结合人TNF-α（溶液态三聚体，UniProt P01375） | 基础 |
| 2. 跨物种反应 | 同一序列在pH 7.4下也结合小鼠TNF-α（79%同源性） | 中等 |
| 3. pH选择性结合 | 在pH 7.4下结合，在pH 6.0下不结合 | 高级 |

排名优先级：pH选择性 > 跨物种 > 亲和力强度。每位参赛者最多提交**20条序列**，截止日期**2026年10月11日**。

---

## 二、靶点分析：TNF-α结构与已有纳米抗体

TNF-α（肿瘤坏死因子α）是自身免疫性疾病的核心靶点，已有多个重磅药物上市：

- **阿达木单抗（Humira）**：全球首个销售额超200亿美元的药物
- **英夫利昔单抗（Remicade）**：嵌合型抗TNF-α抗体
- **Ozoralizumab（Nanozora）**：**全球首个获批的抗TNF纳米抗体**（日本2022年批准），IC50 = 12 pM

### 结构特征

TNF-α以**同源三聚体**形式存在（PDB: 1TNF），受体结合位点位于**相邻单体之间的沟槽（groove）**。

### 已发表的抗TNF VHH晶体结构（Beirnaert et al. 2017, [DOI](https://doi.org/10.3389/fimmu.2017.00867)）

| VHH | PDB | Kd (pM) | 表位 | CDR贡献 |
|-----|-----|---------|------|---------|
| VHH#1 | 5M2I (2.15 A) | 540 | 中央沟槽，接触2个单体 | CDR3主导（599 A2） |
| VHH#2 | 5M2J (1.90 A) | 130 | 中央沟槽 | CDR1/CDR2主导 |
| VHH#3 | 5M2M (2.30 A) | 1500 | 受体位点底部，单单体接触 | CDR2主导（314 A2） |
| Ozoralizumab | 8Z8M | 20.2 | 同VHH#2（95.65%序列同源） | 三价构建体 |

**关键表位残基**（距离 < 3.8 A）：
- 单体A: 20-25, 65-67, 70, 72-74, 77, 79, 81, 83, 88-92, 97, 107, 135-141
- 单体B: 115, 145-147
- **E-F环（残基~140-146）**是受体结合的关键区域

### 跨物种反应性的挑战

**重要发现：所有已发表的抗TNF纳米抗体都是人源特异性的，不与小鼠TNF-α交叉反应。** 这包括ozoralizumab和最新的TNFI-Nbs（NN-223/224）。这意味着竞赛目标2（跨物种反应性）需要**刻意设计**针对人鼠保守残基的接触方式，而非简单移植已有CDR。

人鼠TNF-α序列同源性为79%，但**结合界面处的关键差异**导致了物种特异性。我们的B组和D组设计通过N/S/T富集策略靶向骨架氢键（物种不变），而非侧链特异性接触。

---

## 三、pH选择性设计：组氨酸开关策略

这是本次竞赛最具挑战性的目标，也是我们设计策略的核心创新点。

### 原理

组氨酸（His）的咪唑侧链pKa约为6.0，恰好处于两个目标pH值之间：

```
pH 7.4（生理pH）：His不带电 → 可形成氢键和π-π堆叠 → 正常结合
pH 6.0（肿瘤/内体pH）：His质子化(+1) → 静电排斥 → 结合被破坏
```

### 文献依据

根据Wei等人的研究（[Proteins 2022, 90:1538](https://doi.org/10.1002/prot.26340)），在CDR区域将以下残基突变为His最有效：

1. **色氨酸(W) → His**：最高成功率
2. **精氨酸(R) → His**：高成功率
3. **酪氨酸(Y) → His**：中等成功率

Wei与Sulea进一步开发了**SIpHAB**工具（[mAbs 2024, 16:2404064](https://doi.org/10.1080/19420862.2024.2404064)），基于序列即可预测His突变对pH依赖性结合的影响。

### TNF-α pH开关先例：W1-Humira

Hong等人（[Biomolecules 2021, 11:334](https://doi.org/10.3390/biom11020334)）已直接在**抗TNF-α抗体（adalimumab）**上验证了His开关机制：
- 将CDR关键残基突变为组氨酸，创建了"W1-Humira"
- **体外实验证实**：pH 7.4下正常结合TNF-α，pH 6.0下结合显著减弱
- 这为我们的C/D组设计提供了直接的概念验证

---

## 四、设计策略：四组差异化VHH方案

我们采用cAbBCII10（PDB: 3DWT）作为VHH骨架，这是纳米抗体设计领域公认的金标准框架，具有高热稳定性（Tm > 70°C）和优异的CDR嫁接耐受性。

### 框架区域（80 aa，固定）

| 区域 | 序列 | 长度 |
|------|------|------|
| FR1 | EVQLVESGGGLVQAGGSLRLSCAAS | 25 aa |
| FR2 | WFRQAPGKEREGVS | 14 aa |
| FR3 | RFTISRDNAKNTVYLQMNSLKPEDTAVYYC | 30 aa |
| FR4 | WGQGTQVTVSS | 11 aa |

### 四组设计方案

#### A组（01-05）：强亲和力结合子

- 芳香族残基（W/Y/F）富集的CDR3
- 靶向三聚体界面沟槽
- 无pH工程改造
- **目的**：建立亲和力基线

#### B组（06-10）：跨物种优化

- CDR中富含Asn(N)/Ser(S)/Thr(T)
- 靶向人鼠保守表位
- 避免接触物种差异位点
- **目的**：同时结合人和鼠TNF-α

#### C组（11-15）：温和pH开关

- 每条序列含**1-2个His**替换（W→H或R→H）
- 在保持基础亲和力的同时引入pH敏感性
- **目的**：平衡亲和力与pH选择性

#### D组（16-20）：强pH开关 + 跨物种

- 每条序列含**3-4个His**替换
- 结合跨物种表位优化策略
- **目的**：同时满足三个竞赛目标——最高得分潜力

---

## 五、AIDD工作站工具链

我们的设计流程整合了工作站上的多个AI蛋白质设计工具：

### 工具清单

| 工具 | 路径 | 用途 |
|------|------|------|
| **Boltz-2** | `boltz2/` | 结构预测与亲和力打分 |
| **RFAntibody** | `rfantibody/` | RFdiffusion骨架生成 + ProteinMPNN序列设计 |
| **NanoFlow** | `nanobody-pipeline/` | 四模块VHH设计流程 |
| **LigandMPNN** | `ligandMNPP/` | 配体感知序列优化 |
| **AbMPNN** | `AbMPNN/` | 抗体专用序列设计 |
| **BoltzGen** | `BoltzGen/` | 生成式蛋白质设计与排名 |

### 流水线架构

```
FASTA输入 (20条VHH序列)
    │
    ├── Step 1: 下载靶标结构 (1TNF, 2TNF)
    │
    ├── Step 2: Boltz-2 复合物预测 + 打分
    │   ├── iPTM (界面预测模板匹配)
    │   ├── pAE (预测对齐误差)
    │   └── pLDDT (每残基置信度)
    │
    ├── Step 3: 跨物种验证 (vs 鼠TNF-α)
    │
    ├── Step 4: pH选择性分析
    │   ├── His含量统计
    │   └── SIpHAB预测
    │
    └── Step 5: 最终排名 & 提交准备
```

运行命令：
```bash
cd "Virtual Biotech workflow/targets/tnfa"
bash run_tnfa_pipeline.sh
```

---

## 六、20条VHH候选序列总览

| 编号 | 组别 | 长度 | CDR3长度 | His数 | 核心策略 |
|------|------|------|---------|-------|---------|
| 01 | A | 118 | 18 | 0 | 芳香族CDR3沟槽结合 |
| 02 | A | 117 | 17 | 0 | 离子沟槽插入 |
| 03 | A | 121 | 21 | 0 | 延伸三Y最大界面 |
| 04 | A | 116 | 16 | 0 | 紧凑高亲和力 |
| 05 | A | 120 | 20 | 0 | 平坦宽表位 |
| 06 | B | 118 | 18 | 0 | 保守表位N/S富集 |
| 07 | B | 120 | 20 | 0 | 保守骨架氢键 |
| 08 | B | 116 | 16 | 0 | 紧凑保守沟槽 |
| 09 | B | 117 | 17 | 0 | Q/N/S骨架接触 |
| 10 | B | 120 | 20 | 0 | 宽保守N富集 |
| 11 | C | 118 | 18 | 1 | CDR2 W→H |
| 12 | C | 117 | 17 | 1 | CDR3 W→H |
| 13 | C | 121 | 21 | 2 | CDR1 R→H + CDR3 W→H |
| 14 | C | 116 | 16 | 2 | CDR2 W→H + CDR3 W→H |
| 15 | C | 120 | 20 | 1 | CDR1 W→H |
| 16 | D | 118 | 18 | 3 | 三His跨物种 |
| 17 | D | 120 | 20 | 3 | 三His跨物种 |
| 18 | D | 116 | 16 | 4 | 四His全CDR |
| 19 | D | 120 | 20 | 3 | 三His宽表位 |
| 20 | D | 117 | 17 | 4 | 最强pH选择性 |

---

## 七、关键设计原则总结

### iPTM优化（结构可信度）
- 结构化的CDR3环（含螺旋或β-发夹元素）
- 界面位置放置芳香族残基（W/Y/F）
- 极性与疏水接触平衡

### deltaSASA优化（界面面积）
- 较长的CDR3（16-21残基）
- 跨多个ECL/表位的宽接触面
- 疏水核心 + 极性边缘设计

### pH选择性优化
- W/R/Y → His替换在CDR界面位置
- 每条序列1-4个His，形成梯度
- 利用His的pKa(~6.0)在pH 7.4和6.0之间切换结合能力

### 跨物种反应性
- 靶向人鼠保守残基（主要在单体界面）
- CDR中N/S/T富集，倾向于骨架氢键（物种不变）
- 避免侧链特异性接触物种差异位点

---

## 八、与NK2R竞赛设计的对比

我们同时参与了清华FBS的PDC2026竞赛（NK2R靶标），两个设计策略有显著差异：

| 维度 | NK2R（PDC2026） | TNF-α（Adaptyv 2026） |
|------|-----------------|----------------------|
| 靶标类型 | GPCR（膜蛋白） | 可溶性细胞因子（三聚体） |
| VHH功能 | 激动剂（激活受体） | 结合子（中和活性） |
| pH要求 | 无 | pH 7.4结合/pH 6.0不结合 |
| 跨物种 | 无 | 需结合人和鼠TNF-α |
| 结构数据 | 6个cryo-EM结构 | 多个晶体结构（1TNF等） |
| 设计数 | 5条 | 20条 |
| 截止日期 | 2026-11-11 | 2026-10-11 |

---

## 九、后续步骤与时间线

| 日期 | 任务 |
|------|------|
| 10月6日 | 完成20条序列设计 + 流水线搭建 |
| 10月7-8日 | 运行Boltz-2预测，打分排名 |
| 10月9日 | 跨物种验证 + SIpHAB pH分析 |
| 10月10日 | 最终选择 + 序列优化 |
| 10月11日 | 提交至proteinbase.com |

---

## 十、参考文献

1. Wei W et al. (2022) Antibody mutations favoring pH-dependent binding in solid tumor microenvironments. *Proteins* 90:1538-1546. [DOI](https://doi.org/10.1002/prot.26340)

2. Wei W & Sulea T (2024) Sequence-based engineering of pH-sensitive antibodies for tumor targeting or endosomal recycling applications. *mAbs* 16:2404064. [DOI](https://doi.org/10.1080/19420862.2024.2404064)

3. Hua S et al. (2025) An inflammation-targeting engineered probiotic with high anti-TNF-α nanobody secretion efficacy alleviates ulcerative colitis. *Adv Sci* 12:e12360. [DOI](https://doi.org/10.1002/advs.202512360)

4. El Salamouni NS et al. (2024) Nanobody engineering: computational modelling and design. *FEBS Open Bio* 15:236-253. [DOI](https://doi.org/10.1002/2211-5463.13850)

5. Riccabona JR et al. (2026) Prospecting the protein design landscape. *FEBS Letters*. [DOI](https://doi.org/10.1002/1873-3468.70459)

6. Cia G et al. (2026) The sweet spot in protein design — Where deep learning meets first principles. *FEBS Letters*. [DOI](https://doi.org/10.1002/1873-3468.70429)

---

**本文由SyFlow AIDD平台自动生成，所有序列和数据开源共享。**

**工具链：** Claude Code + Boltz-2 + RFAntibody + NanoFlow + LigandMPNN + SIpHAB

**竞赛链接：** [Anthropic × Adaptyv 2026](https://proteinbase.com/competitions/anthropic-adaptyv-2026/challenges/tnf-alpha)
