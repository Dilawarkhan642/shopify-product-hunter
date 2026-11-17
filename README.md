# 🛍️ Shopify Product Hunter

### AI-Powered Shopify Product Research & Competitor Analysis Platform

**Discover Products. Analyze Competitors. Find Opportunities.**

Shopify Product Hunter is a Python-based e-commerce product research platform built with Streamlit. It helps e-commerce entrepreneurs, dropshippers, and online sellers discover products from Shopify competitor stores, analyze product opportunities, and manage product research through an interactive dashboard.

The platform combines multi-store competitor scanning, product scoring, product research indicators, CSV importing, and SQLite database management into one centralized application.

---

## 📌 Project Overview

Finding potential winning products is one of the biggest challenges in e-commerce.

Shopify Product Hunter aims to simplify this process by collecting publicly accessible product information from Shopify storefronts and organizing it into structured research results.

Users can scan competitor stores, review discovered products, evaluate research indicators, assign opportunity scores, save products, and export their research data.

The goal is to make product research more organized, efficient, and data-driven.

## 🚀 Key Features

### 1. Competitor Store Scanner
- Scan publicly accessible Shopify storefronts.
- Discover product listings from competitor stores.
- Extract product titles, prices, vendors, product types, and product URLs where available.
- Scan multiple competitor stores.
- Configure product scanning limits.
- Handle HTTP errors and rate limits.
- Avoid aggressive repeated requests to competitor websites.

### 2. Product Research & Scoring
- Generate product opportunity scores.
- Categorize products based on their research scores.
- Identify potential product opportunities.
- Display product discounts where available.
- Check available best-seller indicators.
- Detect supported advertising pixels.
- Organize product research results.

**Product scoring categories:**

| Category | Score |
|---|---:|
| Strong Opportunity | 65–100 |
| Promising Opportunity | 40–64 |
| Weak Opportunity | Below 40 |

*These scores are research indicators, not verified sales figures or guarantees of profitability.*

### 3. Multi-Store Product Research
- Add multiple competitor store URLs.
- Scan different Shopify stores from one dashboard.
- Review products collected from different stores.
- Organize competitor research in one place.
- Apply scanning limits to control requests.

### 4. Product Database Management
- Store product research data using SQLite.
- Save discovered products.
- Update existing product records.
- Avoid duplicate records using store and product identifiers.
- Search and filter saved products.
- Sort product information.
- View products in cards or table format.
- Export saved product records.

### 5. CSV Import & Export
- Import product information from CSV files.
- Normalize imported product data.
- Download a CSV import template.
- Review products before saving.
- Export product research results for further analysis.

### 6. Product Research Resources
The platform provides research links to:
- Meta Ads Library
- Google Trends
- Original competitor product pages

These resources help users conduct additional market and advertising research.

### 7. Modern Hybrid Dashboard
- Modern green-themed interface.
- Interactive Streamlit dashboard.
- Store Scanner section.
- CSV Import section.
- Product Database section.
- Product cards and table views.
- Search, sorting, filtering, and pagination.
- Responsive wide-layout dashboard.

---

## 🖥️ Dashboard Modules

| Module | Description |
|---|---|
| Store Scanner | Scan Shopify competitor storefronts |
| CSV Import | Import external product research data |
| Product Database | View and manage saved products |

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application development |
| Streamlit | Interactive web application |
| Pand
