# EHR SQL Benchmark (NAACL 2024)

## Overview

Curated benchmark with **100 examples** from the Reliable Text-to-SQL on Electronic Health Records shared task (Clinical NLP Workshop @ NAACL 2024).

**Source**: [ehrsql-2024](https://github.com/glee4810/ehrsql-2024) | **Database**: MIMIC-IV Demo

## Data Schema

| Column | Description |
|--------|-------------|
| Query | Natural language question about EHR data |
| Chat Conversation | Link to model interaction |
| Model Answer | AI-generated response |
| Golden Truth | Expected correct answer |
| Golden Truth SQL Query | Ground truth SQL query |
| Correct/Incorrect | 1 = correct, 0 = incorrect |
| Incorrect Note | Error analysis when applicable |

## Query Examples

- Patient-specific: Lab values, medications, procedures
- Temporal: Time-based analysis, trends
- Aggregate: Population statistics
- Complex joins: Multi-table EHR relationships
