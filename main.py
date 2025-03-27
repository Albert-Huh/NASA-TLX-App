import sys, json, csv, os
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (
    QWidget, QApplication, QWizard, QWizardPage, QVBoxLayout, QLabel,
    QSlider, QRadioButton, QButtonGroup, QHBoxLayout, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QSize
from datetime import datetime

# Constants
FACTORS = [
    "Mental Demand", "Physical Demand", "Temporal Demand",
    "Performance", "Effort", "Frustration"
]

DEFINITIONS = {
    "Mental Demand": "How much mental and perceptual activity was required?",
    "Physical Demand": "How much physical activity was required?",
    "Temporal Demand": "How much time pressure did you feel?",
    "Performance": "How successful were you in accomplishing the goals?",
    "Effort": "How hard did you have to work?",
    "Frustration": "How insecure, discouraged, or stressed did you feel?"
}

# Ensure data directory exists
DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

class TLXSlider(QWidget):
    def __init__(self, min_val=0, max_val=100, step=5, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.value = 50  # Default
        self.setMinimumSize(QSize(700, 100))
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        y = height // 2
        
        # Draw main line and ticks
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(10, y, width - 10, y)
        num_steps = (self.max_val - self.min_val) // self.step
        step_width = (width - 20) / num_steps
        for i in range(num_steps + 1):
            x = 10 + i * step_width
            painter.drawLine(int(x), y - 7, int(x), y + 7)
        
        # Draw handle
        handle_x = 10 + ((self.value - self.min_val) / (self.max_val - self.min_val)) * (width - 20)
        painter.setPen(QPen(Qt.red, 4))
        painter.drawLine(int(handle_x), y - 15, int(handle_x), y + 15)
    
    def mousePressEvent(self, event):
        self.update_value(event.position().x())
    
    def mouseMoveEvent(self, event):
        self.update_value(event.position().x())
    
    def update_value(self, x):
        width = self.width() - 20
        relative_x = min(max(0, x - 10), width)
        self.value = round((self.min_val + (relative_x / width) * (self.max_val - self.min_val)) / self.step) * self.step
        self.update()
    
    def get_value(self):
        return self.value

class TLXApp(QWizard):
    def __init__(self, use_weighting=True):
        super().__init__()
        self.setWindowTitle("NASA-TLX Survey")
        self.resize(900, 600)
        self.use_weighting = use_weighting
        self.ratings = {}
        self.weights = {factor: 0 for factor in FACTORS}

        # Create pages
        for factor in FACTORS:
            self.addPage(self.create_rating_page(factor))
        if use_weighting:
            self.addPage(self.create_weighting_page())
        self.button(QWizard.FinishButton).clicked.connect(self.save_results)

    def create_rating_page(self, factor):
        page = QWizardPage()
        page.setTitle(f"Rate: {factor}")
        layout = QVBoxLayout()
        
        label = QLabel(DEFINITIONS[factor])
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        slider = TLXSlider()
        layout.addWidget(slider)
        
        labels_layout = QHBoxLayout()
        labels_layout.addWidget(QLabel("Low" if factor != "Performance" else "Good"))
        labels_layout.addStretch()
        labels_layout.addWidget(QLabel("High" if factor != "Performance" else "Poor"))
        layout.addLayout(labels_layout)
        
        page.setLayout(layout)
        page.slider = slider
        return page

    def create_weighting_page(self):
        page = QWizardPage()
        page.setTitle("Pairwise Weighting Comparison")
        layout = QVBoxLayout()
        
        self.button_groups = []
        for i, f1 in enumerate(FACTORS):
            for f2 in FACTORS[i+1:]:
                h_layout = QHBoxLayout()
                btn_grp = QButtonGroup()
                rb1, rb2 = QRadioButton(f1), QRadioButton(f2)
                btn_grp.addButton(rb1)
                btn_grp.addButton(rb2)
                h_layout.addWidget(rb1)
                h_layout.addWidget(rb2)
                layout.addLayout(h_layout)
                self.button_groups.append(btn_grp)
                btn_grp.buttonClicked.connect(self.update_weights)
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                layout.addWidget(line)
        
        page.setLayout(layout)
        return page

    def update_weights(self):
        self.weights = {factor: sum(1 for btn_grp in self.button_groups if btn_grp.checkedButton() and btn_grp.checkedButton().text() == factor) for factor in FACTORS}
        if sum(self.weights.values()) > 15:
            QMessageBox.warning(self, "Error", "Total selections exceed 15. Adjust your choices.")

    def save_results(self):
        self.ratings = {factor: self.page(FACTORS.index(factor)).slider.get_value() for factor in FACTORS}
        adjusted_ratings = {factor: self.ratings[factor] * self.weights[factor] for factor in FACTORS} if self.use_weighting else {}
        weighted_rating = sum(adjusted_ratings.values()) / 15 if self.use_weighting else sum(self.ratings.values()) / len(FACTORS)
        
        result_data = {
            'timestamp': datetime.now().isoformat(),
            'ratings': self.ratings,
            'weights': self.weights if self.use_weighting else {},
            'adjusted_ratings': adjusted_ratings if self.use_weighting else {},
            'weighted_rating': weighted_rating
        }
        self.save_to_files(result_data)

    def save_to_files(self, result_data):
        json_file = os.path.join(DATA_DIR, 'nasa_tlx_results.json')
        csv_file = os.path.join(DATA_DIR, 'nasa_tlx_results.csv')
        
        # Save JSON
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                data = json.load(f)
        else:
            data = []
        data.append(result_data)
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=4)
        
        # Prepare CSV Data
        csv_data = {'timestamp': result_data['timestamp']}
        for factor in FACTORS:
            csv_data[factor] = result_data['ratings'].get(factor, '')
        if self.use_weighting:
            for factor in FACTORS:
                csv_data[f"adjusted_{factor}"] = result_data['adjusted_ratings'].get(factor, '')
        csv_data['weighted_rating'] = result_data['weighted_rating']
        
        # Save CSV
        file_exists = os.path.exists(csv_file)
        with open(csv_file, 'a', newline='') as f:
            fieldnames = ['timestamp'] + FACTORS + ([f"adjusted_{factor}" for factor in FACTORS] if self.use_weighting else []) + ['weighted_rating']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(csv_data)

if __name__ == "__main__":
    def main():
        app = QApplication(sys.argv)
        wizard = TLXApp(use_weighting=True)
        wizard.show()
        sys.exit(app.exec())
    main()
