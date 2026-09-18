# \# NIDS-ML

# 

# Network Intrusion Detection System using Machine Learning, FastAPI, React, SQLite, WebSockets, and real-time network flow monitoring.

# 

# NIDS-ML detects potentially malicious network traffic using machine-learning models trained on the UNSW-NB15 dataset. It provides both dataset-based inference and controlled live monitoring, with predictions exposed through a FastAPI backend and visualized through a React dashboard.

# 

# \## Overview

# 

# NIDS-ML implements an end-to-end intrusion detection pipeline:

# 

# ```text

# UNSW-NB15 Dataset

# &#x20;       │

# &#x20;       ▼

# Data Audit

# &#x20;       │

# &#x20;       ▼

# Leakage-Safe Preprocessing

# &#x20;       │

# &#x20;       ▼

# Machine Learning Models

# &#x20;       │

# &#x20;       ├── Binary Detection

# &#x20;       │      └── Normal / Attack

# &#x20;       │

# &#x20;       └── Multiclass Detection

# &#x20;              └── Attack Category

# &#x20;       │

# &#x20;       ▼

# FastAPI Inference Layer

# &#x20;       │

# &#x20;       ├── SQLite Persistence

# &#x20;       ├── REST API

# &#x20;       └── WebSocket Alerts

# &#x20;       │

# &#x20;       ▼

# React Dashboard

# &#x20;       │

# &#x20;       ├── Dashboard

# &#x20;       ├── Detections

# &#x20;       ├── Analytics

# &#x20;       ├── Model Metrics

# &#x20;       └── Live Monitoring

# Features

# UNSW-NB15 based intrusion detection

# Leakage-safe preprocessing pipeline

# Binary Normal/Attack classification

# Multiclass attack-category classification

# Logistic Regression, Random Forest, and XGBoost comparison

# XGBoost-based production inference

# FastAPI REST API

# Pydantic request/response validation

# SQLite prediction history

# Detection filtering and detail views

# CSV detection export

# Attack analytics

# Model metrics and feature importance

# WebSocket real-time prediction alerts

# Controlled live packet capture using Scapy/Npcap

# Flow aggregation before inference

# Live monitoring start/stop controls

# React + TypeScript dashboard

# Dataset and live prediction modes

# Environment-based live-capture configuration

# Technology Stack

# Machine Learning

# Python 3.12

# pandas

# NumPy

# scikit-learn

# XGBoost

# joblib

# SciPy

# Backend

# FastAPI

# Uvicorn

# Pydantic

# SQLAlchemy

# SQLite

# WebSockets

# Live Monitoring

# Scapy

# Npcap

# Flow aggregation and timeout-based flow finalization

# Frontend

# React

# TypeScript

# Vite

# CSS

# Project Structure

# NIDS-ML/

# │

# ├── backend/

# │   ├── api/

# │   │   ├── inference.py

# │   │   ├── main.py

# │   │   ├── schemas.py

# │   │   └── websocket.py

# │   │

# │   ├── app/

# │   │   ├── config.py

# │   │   ├── database.py

# │   │   └── models/

# │   │       └── prediction\_event.py

# │   │

# │   ├── data/

# │   │   ├── raw/

# │   │   │   └── UNSW-NB15 CSV files

# │   │   ├── audit\_report.json

# │   │   ├── audit\_report.txt

# │   │   └── feature\_schema.json

# │   │

# │   ├── live/

# │   │   ├── capture.py

# │   │   ├── context\_tracker.py

# │   │   ├── flow\_adapter.py

# │   │   ├── flow\_aggregator.py

# │   │   ├── flow\_manager.py

# │   │   ├── packet\_adapter.py

# │   │   ├── predict\_live.py

# │   │   └── service.py

# │   │

# │   ├── ml/

# │   │   ├── artifacts/

# │   │   ├── audit.py

# │   │   ├── preprocess.py

# │   │   └── validate.py

# │   │

# │   └── requirements.txt

# │

# ├── docs/

# │   ├── data-preprocessing.md

# │   └── phase2\_report.md

# │

# ├── frontend/

# │   ├── src/

# │   │   ├── App.tsx

# │   │   ├── api.ts

# │   │   └── ...

# │   ├── package.json

# │   └── vite.config.ts

# │

# ├── .env.example

# ├── .gitignore

# └── README.md

# Dataset

# 

# The primary dataset is UNSW-NB15.

# 

# The dataset contains network-flow features and labels for normal and malicious traffic.

# 

# The implemented pipeline uses:

# 

# id as an identifier and excludes it from model features.

# label as the binary target.

# attack\_cat as the multiclass target.

# 42 raw model input features after excluding id, label, and attack\_cat.

# 39 numeric features.

# 3 categorical features:

# proto

# service

# state

# 

# The preprocessing pipeline produces 192 transformed features.

# 

# Dataset Split

# 

# The supplied UNSW-NB15 training data is divided into:

# 

# Training partition:    140,272 rows

# Validation partition:  35,069 rows

# Official test set:     82,332 rows

# 

# The validation split uses stratification with random\_state=42.

# 

# Preprocessing is fitted only on the training partition.

# 

# The official UNSW-NB15 test set remains untouched during model selection.

# 

# Data Quality and Leakage Controls

# 

# The dataset audit verified:

# 

# No missing values in the supplied training data.

# No missing values in the supplied testing data.

# Zero duplicate rows in the supplied training data.

# Zero duplicate rows in the supplied testing data.

# 

# The preprocessing workflow follows:

# 

# Raw Data

# &#x20;  │

# &#x20;  ▼

# Audit

# &#x20;  │

# &#x20;  ▼

# Remove identifier / target columns

# &#x20;  │

# &#x20;  ▼

# Train / Validation Split

# &#x20;  │

# &#x20;  ▼

# Fit preprocessing on training partition only

# &#x20;  │

# &#x20;  ├── Numeric → Median Imputation → StandardScaler

# &#x20;  │

# &#x20;  └── Categorical → Most-Frequent Imputation → OneHotEncoder

# &#x20;                                     │

# &#x20;                                     ▼

# &#x20;                             Transformed Features

# 

# This prevents validation/test information from being used to fit preprocessing parameters.

# 

# Machine Learning

# 

# Three binary classification approaches were compared:

# 

# Logistic Regression

# Random Forest

# XGBoost

# 

# The primary model was selected using validation F1 score rather than accuracy alone.

# 

# Binary Validation Results

# Model	Accuracy	Precision	Recall	F1	False Positive Rate

# Logistic Regression	0.932533	0.949948	0.950982	0.950465	0.106786

# Random Forest	0.957170	0.973656	0.963132	0.968366	0.055536

# XGBoost	0.962132	0.967094	0.977628	0.972332	0.070893

# 

# XGBoost was selected as the primary binary inference model because it achieved the highest validation F1 score among the compared models.

# 

# The model configuration is documented in the project training artifacts and reports.

# 

# Multiclass Detection

# 

# The multiclass model predicts ten UNSW-NB15 categories:

# 

# Analysis

# Backdoor

# DoS

# Exploits

# Fuzzers

# Generic

# Normal

# Reconnaissance

# Shellcode

# Worms

# 

# The multiclass XGBoost model uses the same leakage-safe preprocessing pipeline.

# 

# Multiclass Validation Results

# Accuracy:          0.833984

# Weighted Precision: 0.831544

# Weighted Recall:    0.833984

# Weighted F1:        0.820354

# Macro F1:           0.618551

# 

# The difference between weighted F1 and macro F1 reflects the strong class imbalance in UNSW-NB15, particularly for rare categories such as Worms, Shellcode, Backdoor, and Analysis.

# 

# The project therefore reports per-class metrics rather than relying only on overall accuracy.

# 

# Model Feature Importance

# 

# The binary XGBoost model's transformed feature importance is available through the API and dashboard.

# 

# The most influential transformed features in the trained model include:

# 

# sttl

# ct\_state\_ttl

# dttl

# proto\_tcp

# proto\_unas

# service\_dns

# state\_CON

# proto\_rvd

# ct\_dst\_sport\_ltm

# proto\_cbt

# 

# The importance values are calculated from the trained XGBoost model using the transformed feature names generated by the preprocessing pipeline.

# 

# Backend API

# 

# The FastAPI backend provides the following endpoints.

# 

# Health

# GET /health

# 

# Returns service health information.

# 

# Dashboard Summary

# GET /api/dashboard/summary

# 

# Returns aggregate dashboard statistics and recent detection events.

# 

# Prediction

# POST /api/predict

# 

# Runs binary and multiclass inference and persists the prediction.

# 

# Example request:

# 

# {

# &#x20; "mode": "dataset",

# &#x20; "features": {

# &#x20;   "dur": 0.1,

# &#x20;   "proto": "tcp",

# &#x20;   "service": "http",

# &#x20;   "state": "FIN"

# &#x20; }

# }

# 

# The complete feature schema must be supplied for inference.

# 

# Batch Prediction

# POST /api/predict/batch

# 

# Runs multiple predictions in a single request.

# 

# Detection History

# GET /api/detections

# 

# Supports querying stored prediction events.

# 

# Detection Detail

# GET /api/detections/{id}

# 

# Returns a specific persisted detection.

# 

# Detection Export

# GET /api/detections/export.csv

# 

# Exports persisted detections as CSV.

# 

# Attack Analytics

# GET /api/analytics/attacks

# 

# Returns attack-category statistics.

# 

# Model Metrics

# GET /api/model/metrics

# 

# Returns the stored model evaluation information.

# 

# Model Features

# GET /api/model/features

# 

# Returns transformed feature importance information.

# 

# Live Status

# GET /live/status

# 

# Returns live-monitoring configuration and runtime status.

# 

# Live Start

# POST /live/start

# 

# Starts controlled live packet capture using the configured interface.

# 

# Live Stop

# POST /live/stop

# 

# Stops live capture safely.

# 

# WebSocket Alerts

# WS /ws/alerts

# 

# Connected dashboard clients receive prediction events when new detections are persisted.

# 

# Database

# 

# SQLite is used for local persistence.

# 

# Prediction events contain fields including:

# 

# id

# timestamp

# mode

# source\_ip

# destination\_ip

# protocol

# binary\_prediction

# binary\_label

# binary\_confidence

# attack\_category

# multiclass\_confidence

# severity

# model\_version

# 

# The database allows the dashboard to display historical detections and analytics.

# 

# Live Monitoring

# 

# NIDS-ML supports controlled live packet capture using Scapy and Npcap.

# 

# The live pipeline is:

# 

# Network Interface

# &#x20;      │

# &#x20;      ▼

# Packet Capture

# &#x20;      │

# &#x20;      ▼

# Packet Adapter

# &#x20;      │

# &#x20;      ▼

# Flow Aggregation

# &#x20;      │

# &#x20;      ▼

# Flow Timeout

# &#x20;      │

# &#x20;      ▼

# UNSW-NB15 Feature Adapter

# &#x20;      │

# &#x20;      ▼

# Preprocessing

# &#x20;      │

# &#x20;      ▼

# Binary + Multiclass XGBoost

# &#x20;      │

# &#x20;      ▼

# SQLite

# &#x20;      │

# &#x20;      ├── REST API

# &#x20;      └── WebSocket

# &#x20;             │

# &#x20;             ▼

# &#x20;       React Dashboard

# Windows Requirements

# 

# Live packet capture requires:

# 

# Windows

# Npcap

# A supported network interface

# Appropriate permissions for packet capture

# Scapy

# 

# The interface is configured through .env.

# 

# Live Feature Limitations

# 

# The UNSW-NB15 dataset contains features that depend on flow context and application-layer information.

# 

# Some live-mode values are therefore approximated when they cannot be directly reconstructed from the captured traffic.

# 

# Examples include:

# 

# sloss

# dloss

# trans\_depth

# response\_body\_len

# is\_ftp\_login

# ct\_ftp\_cmd

# ct\_flw\_http\_mthd

# 

# Several contextual ct\_\* features are also maintained through short-term live-flow tracking.

# 

# Therefore:

# 

# Live-mode feature extraction is an approximation of the UNSW-NB15 feature semantics.

# 

# The system should not be interpreted as producing perfectly equivalent UNSW-NB15 features from arbitrary real-world traffic.

# 

# This limitation is important when interpreting live predictions.

# 

# Severity

# 

# Predictions are assigned a severity level for dashboard presentation.

# 

# The API considers binary classification, multiclass classification, and confidence when determining the displayed severity.

# 

# Severity is intended as a presentation/triage signal and is not an automated blocking mechanism.

# 

# Frontend

# 

# The React dashboard provides:

# 

# Dashboard overview

# Live capture controls

# Threat statistics

# Recent detections

# Detection history

# Detection filtering

# Detection details

# CSV export

# Attack-category analytics

# Model performance information

# Feature importance

# Live WebSocket alerts

# System/live configuration status

# Loading and API error handling

# 

# The frontend communicates with FastAPI rather than using hard-coded detection statistics.

# 

# Installation

# Requirements

# 

# Recommended environment:

# 

# Python 3.12.x

# Node.js 24.x

# npm 11.x

# Git

# 

# For live monitoring on Windows:

# 

# Npcap

# Clone

# git clone https://github.com/santanu949/NIDS.git

# cd NIDS

# Backend Environment

# 

# Create the virtual environment:

# 

# python -m venv .venv

# 

# Activate it:

# 

# .\\.venv\\Scripts\\Activate.ps1

# 

# Install backend dependencies:

# 

# pip install -r backend\\requirements.txt

# Environment Configuration

# 

# Copy .env.example to .env.

# 

# Configure the live network interface:

# 

# NIDS\_LIVE\_INTERFACE=YOUR\_NETWORK\_INTERFACE

# NIDS\_LIVE\_FLOW\_TIMEOUT=5

# 

# The interface value must match a valid Scapy/Npcap interface on the machine.

# 

# For dataset-only use, live capture does not need to be started.

# 

# Start Backend

# 

# From the project root:

# 

# .\\.venv\\Scripts\\python.exe -m uvicorn backend.api.main:app --reload --port 8000

# 

# API documentation:

# 

# http://127.0.0.1:8000/docs

# Frontend

# 

# Open a second terminal:

# 

# cd frontend

# npm install

# npm run dev

# 

# The Vite development server normally runs at:

# 

# http://localhost:5173/

# Basic Verification

# 

# Check the backend:

# 

# GET /health

# 

# The expected response indicates that the API service is healthy.

# 

# The project can then be verified through:

# 

# Dashboard loading

# Dataset prediction

# Detection persistence

# Detection history

# Analytics

# Model metrics

# WebSocket alert delivery

# Live capture start/stop

# Live flow prediction when a supported capture environment is available

# Security and Ethical Considerations

# 

# This project is intended for defensive security research, education, and controlled network monitoring.

# 

# Live packet capture should only be performed on systems and networks for which the operator has authorization.

# 

# The project does not implement automatic blocking or countermeasures.

# 

# The system should be deployed in an isolated or controlled environment when generating attack traffic for testing.

# 

# Sensitive payloads and credentials should not be stored in logs.

# 

# Flow metadata should be preferred over collecting unnecessary packet payload content.

# 

# Limitations

# 

# Important limitations include:

# 

# UNSW-NB15 is a benchmark dataset and does not represent every modern network environment.

# Dataset distribution may differ from production traffic.

# Rare attack classes have substantially less validation support.

# Multiclass macro F1 is lower than weighted F1 because of class imbalance.

# Live feature extraction approximates some UNSW-NB15 features.

# Live predictions should therefore be interpreted as experimental/controlled monitoring rather than definitive forensic conclusions.

# Model confidence is not equivalent to real-world probability of an attack.

# No automated response or blocking mechanism is implemented.

# Npcap/Scapy availability and interface permissions affect live monitoring.

# Documentation

# 

# Additional project documentation is available under docs/.

# 

# Current documentation includes:

# 

# Data preprocessing methodology

# Phase 2 validation/reporting

# Model training and evaluation artifacts

# Dataset audit information

# Development Workflow

# 

# The project was implemented in phases:

# 

# 1\. Environment + Repository

# 2\. Dataset Acquisition + Data Audit

# 3\. Preprocessing Pipeline

# 4\. Train + Compare ML Models

# 5\. Binary + Multiclass Detection

# 6\. FastAPI

# 7\. Database

# 8\. React Dashboard

# 9\. Live Monitoring + Alerts

# 10\. Testing, Security, Packaging + Documentation

# 

# Git history contains checkpoints for the major implementation phases.

# 

# Project Status

# 

# Core implementation:

# 

# Dataset audit                    Complete

# Preprocessing                    Complete

# Binary ML detection              Complete

# Multiclass detection             Complete

# FastAPI inference                Complete

# Database persistence             Complete

# React dashboard                  Complete

# WebSocket alerts                 Complete

# Controlled live monitoring       Complete

# Dependency specification         Complete

# 

# Final academic documentation and submission artifacts may continue to evolve independently of the core implementation.

# 

# License

# 

# This repository does not currently declare a software license.

# 

# If the project is intended for public reuse or distribution, an appropriate license should be added after confirming the licensing requirements of the dataset, dependencies, and project contributors.

# 

# Disclaimer

# 

# NIDS-ML is a machine-learning based intrusion detection research and demonstration system.

# 

# Its predictions should not be treated as definitive evidence of malicious activity.

# 

# The system is intended to assist monitoring and analysis, not replace human investigation or established security controls.

