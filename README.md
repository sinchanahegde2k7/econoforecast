# EconoForecast: AI-Based Economic Growth Forecasting and   Analysis System Using Machine Learning 
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Deployment](https://img.shields.io/badge/Render-Hosted-46E3B7?style=flat&logo=render&logoColor=white)](https://render.com)

A full-stack web application designed to analyze and project key macroeconomic indicators for India—specifically GDP Growth, Inflation, and Unemployment—using a hybrid approach of classical econometrics and modern deep learning.

## 🌐 Live Application

**Live Demo:** [Click here to try!](https://econoforecast.onrender.com)

**Test Credentials:**
* **User Access:** `user@econoforecast.com` / `user@123`

> **Hosting Note:** This application is deployed on a free-tier Render instance. If the site has not been visited recently, the server may enter a sleep state. Please allow 30–60 seconds for the initial load as the container wakes up. 

## 📖 Project Overview

Economic policymaking and business strategy rely heavily on accurate macroeconomic forecasting. Traditional econometric models often struggle with the non-linear, complex shifts inherent in real-world economic data. EconoForecast was developed as a comprehensive MCA capstone project to address this gap by evaluating how well different classes of predictive models perform on real historical data. 

The platform directly ingests historical time-series data from the World Bank Open Data API, processes it, and generates future projections using three distinct modeling architectures. It features a secure, role-based dashboard where users can view forecast visualizations and administrators can monitor system activity.

## 🧠 Forecasting Architectures

The system evaluates economic indicators using a progression of models, moving from simple baselines to complex neural networks:

1. **Linear Regression (Baseline):** Serves as a straightforward, interpretable baseline to establish the foundational trend of the indicator.
2. **ARIMA (Classical Econometric):** Captures auto-correlation, differencing, and moving averages, providing a strong benchmark for traditional time-series forecasting.
3. **LSTM (Deep Learning):** A Long Short-Term Memory recurrent neural network designed to capture complex, non-linear dependencies and long-term patterns in the economic data.

**Evaluation Metrics:** Models are benchmarked against one another using Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and the Coefficient of Determination (R²). 

## ⚙️ Core Features

* **Live Data Ingestion:** Automated fetching of historical economic data (GDP, Inflation, Unemployment) via the World Bank REST API.
* **Multi-Model Inference:** Generates and visualizes comparative forecasts across all three model types simultaneously.
* **Role-Based Access Control (RBAC):** Distinct dashboards for standard users (viewing forecasts) and administrators (tracking usage logs and system activity).
* **Interactive Visualizations:** Dynamic, responsive charting of historical data and future projections.
* **Cloud-Native Database:** Fully managed PostgreSQL integration for persistent storage of user data, indicator histories, and audit logs.

## 🛠️ Technology Stack

* **Backend:** Python, Flask, SQLAlchemy (ORM)
* **Data Processing & ML:** Pandas, NumPy, Scikit-Learn, Statsmodels, TensorFlow/Keras
* **Database:** PostgreSQL
* **Frontend:** HTML5, CSS3, Bootstrap/Tailwind, Chart.js
* **Deployment:** Render (Web Service & Managed Database)

## 🎓 Academic Context

This repository contains the source code, database schemas, and trained models developed for this project. It demonstrates the practical implementation of end-to-end machine learning pipelines, cloud deployment, and full-stack web development.
