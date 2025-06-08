# EHRSQL 2024 Benchmark for M3 MCP Tools

This benchmark evaluates **M3 MCP tools performance** using the EHRSQL 2024 dataset, which contains real-world medical questions designed for MIMIC-IV databases.

## 🎯 Purpose

**What we're testing:** How well M3 MCP tools help LLMs answer medical database questions through tool-assisted exploration and querying.

**Why this matters:** MCP tools should make complex database tasks easier and more accurate by providing:
- Schema exploration tools
- Safe query execution tools
- Data validation and error handling
- Structured result formatting

## 📊 Dataset: EHRSQL 2024

### Source
- **Repository:** [glee4810/ehrsql-2024](https://github.com/glee4810/ehrsql-2024)
- **Database:** MIMIC-IV demo (compatible with your local database)
- **Domain:** Electronic Health Records (EHR) questions

### Dataset Structure

#### File Organization
```
dataset/ehrsql_data/
├── mimic_iv_train_data.json     # Training questions
├── mimic_iv_train_label.json    # Training SQL queries
├── mimic_iv_valid_data.json     # Validation questions (used for evaluation)
├── mimic_iv_valid_label.json    # Validation SQL queries
├── mimic_iv_test_data.json      # Test questions
└── mimic_iv_tables.json         # Database schema information
```

#### Data Format

**Questions File (`*_data.json`):**
```json
{
  "version": "1.0.5",
  "data": [
    {
      "id": "b9c136c1e1d19649caabdeb4",
      "question": "What is patient 10021487's monthly average bilirubin, direct levels since 05/2100?"
    }
  ]
}
```

**Labels File (`*_label.json`):**
```json
{
  "b9c136c1e1d19649caabdeb4": "SELECT AVG(labevents.valuenum) FROM labevents WHERE labevents.hadm_id IN (SELECT...)"
}
```

**Combined Processing:**
Our loader merges these into complete records:
```python
{
  "id": "b9c136c1e1d19649caabdeb4",
  "question": "What is patient 10021487's monthly average...",
  "query": "SELECT AVG(labevents.valuenum) FROM...",  # Expected SQL
  "db_id": "mimic_iv",
  "is_impossible": False  # Whether question is answerable
}
```

### Dataset Statistics
- **Training:** 5,124 questions
- **Validation:** 1,163 questions
- **Test:** 1,167 questions
- **All questions target MIMIC-IV schema** ✅ (No filtering needed!)

## 🔧 MCP Tools Evaluation

### What Gets Tested

1. **Tool Discovery:** Can the LLM find and understand available MCP tools?
2. **Schema Exploration:** Does it use tools to explore database structure?
3. **Query Building:** Does it leverage tools to construct and validate queries?
4. **Error Handling:** How does it respond to tool failures or invalid queries?
5. **Answer Quality:** Are the final answers accurate and complete?

### Evaluation Metrics

#### Primary MCP Metrics:
- **MCP Session Success Rate:** % of sessions where MCP tools work properly
- **Tool Usage Frequency:** Which tools are used most often
- **Tool Success Rate:** % of tool calls that succeed vs fail
- **Average Tools per Question:** How many tools needed per question
- **Unique Tools Used:** Diversity of tool usage

#### Secondary Quality Metrics:
- **Answer Completeness:** Does the LLM provide full answers?
- **Schema Understanding:** Does it correctly identify relevant tables/columns?
- **Query Accuracy:** Are any generated SQL queries syntactically valid?

## 🚀 Usage

### Prerequisites

**1. Install Goose CLI:**
```bash
# Install Goose CLI from Block (MCP client)
curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash

# Verify installation
goose --version

# Make sure ~/.local/bin is in your PATH
export PATH="$HOME/.local/bin:$PATH"
```

**2. M3 MCP Server** configured for MIMIC-IV demo database

**3. Configure Goose with M3 MCP server:**
```bash
# Run from M3 project root
python benchmarks/setup_goose_mcp.py
```

**4. EHRSQL 2024 dataset** downloaded

### Download Dataset
```bash
cd benchmarks/ehrsql
python -m dataset.download
```

### Run Benchmark
```bash
# Quick test (1 question)
python run_mimic_iv_demo_evaluation.py --max-questions 1

# Small evaluation (10 questions)
python run_mimic_iv_demo_evaluation.py --max-questions 10

# Full validation set (1,163 questions)
python run_mimic_iv_demo_evaluation.py --split valid

# Test set evaluation
python run_mimic_iv_demo_evaluation.py --split test
```

### View Results

Results are saved to `results/mimic_iv_demo_goose_TIMESTAMP/`:

```
results/mimic_iv_demo_goose_20240607_143022/
├── detailed_results.json           # Full evaluation data
├── summary.json                    # Aggregate metrics
├── questions_and_sql.json          # Question-answer pairs
└── conversation_logs/              # Full LLM conversations
    ├── question_1_conversation.txt
    ├── question_2_conversation.txt
    └── ...
```

**To see the full LLM conversation:** Check the `conversation_logs/` directory for complete Goose session transcripts showing tool usage.

## 📁 File Structure

```
benchmarks/ehrsql/
├── README.md                       # This file
├── run_mimic_iv_demo_evaluation.py # Main evaluation script
├── dataset/
│   ├── download.py                 # Dataset downloader
│   └── ehrsql_data/               # Downloaded EHRSQL files
├── evaluators/
│   └── goose_evaluator.py         # MCP tools evaluator
└── results/                       # Evaluation outputs
```

## 🎯 Expected Results

A successful MCP tools evaluation should show:

- **High tool usage:** LLM actively uses multiple M3 tools per question
- **Effective exploration:** Tools used for schema discovery before querying
- **Error recovery:** LLM handles tool failures gracefully
- **Quality answers:** Final answers are relevant and well-structured

Example successful session:
```
Tools used: ['m3_get_schema', 'm3_query_database', 'm3_validate_query']
Successful tool calls: 5
Failed tool calls: 0
Final answer: "Patient 10021487's average bilirubin levels since 05/2100 is 2.4 mg/dL based on 8 lab measurements."
```

## 🔍 Troubleshooting

**"Goose CLI not found"**
→ Install Goose: `curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash`
→ Verify: `goose --version`
→ If not in PATH, check: `ls ~/.local/bin/goose` and add `export PATH="$HOME/.local/bin:$PATH"`

**"M3 MCP server not configured"**
→ Run `python benchmarks/setup_goose_mcp.py` from project root

**"Dataset not found"**
→ Run `python -m dataset.download` to download EHRSQL 2024

**"Empty conversation logs"**
→ Check that M3 MCP server is running and accessible

**"Session failed: unexpected argument '--provider'"**
→ Update to latest Goose version: `curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash`
