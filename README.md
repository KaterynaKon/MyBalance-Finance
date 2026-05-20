# 💰 MyBalance

A smart personal finance web application built with Flask that helps users track income, expenses, and financial history with powerful reporting, file attachments, and OCR-based data extraction.

---

## ✨ Key Features

### 🔐 Authentication
- User registration and login system  
- Secure password hashing using Werkzeug  
- Session-based authentication  

---

### 💸 Transactions Management
- Add income and expenses  
- Edit and delete transactions  
- Categorized financial tracking  
- Attach receipts or files to transactions  

---

### 📊 Analytics & Reporting
- Filter transactions by date range  
- Predefined time presets (This week, Last 7 days, Month, etc.)  
- Category-based financial reports  
- Income vs expenses balance calculation  

---

### 📎 File Handling
- Upload attachments (images, receipts, PDFs)  
- Secure file storage  
- Delete or replace attachments  

---

### 📄 Data Import / Export
- Import transactions via CSV  
- Export data to CSV or Excel formats  
- Date-filtered export support  

---

### 🧠 OCR Integration
- Extract transaction data from receipt images using Tesseract OCR  
- Auto-detection of amount, date, and merchant (when possible)  

---

## 🛠 Tech Stack

- **Backend:** Flask (Python)  
- **Database:** SQLite  
- **Authentication:** Flask sessions + Werkzeug security  
- **File Handling:** Python OS, Werkzeug  
- **Data Handling:** Pandas  
- **OCR:** Tesseract (pytesseract)  
- **CSV Processing:** Python csv module  
