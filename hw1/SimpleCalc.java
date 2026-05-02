import java.awt.*;
import java.awt.event.*;

public class SimpleCalc extends Frame implements ActionListener {
    
    // Display
    private TextField display = new TextField("0");
    private Label memLabel = new Label(" ");
    
    // Calculator state
    private double firstNumber = 0;
    private double memory = 0;
    private char operator = ' ';
    private boolean newNumber = true;
    
    // Button arrays
    private String[] digitText = {"7", "8", "9", "4", "5", "6", "1", "2", "3", "0", "+/-", "."};
    private String[] operatorText = {"/", "sqrt", "*", "%", "-", "1/X", "+", "="};
    private String[] memoryText = {"MC", "MR", "MS", "M+"};
    private String[] specialText = {"Back", "C", "CE"};
    
    // Layout constants
    private final int WIDTH = 350, HEIGHT = 400;
    
    public SimpleCalc() {
        super("Simple Calculator");
        setLayout(null);
        setSize(WIDTH, HEIGHT);
        
        setupDisplay();
        setupButtons();
        
        addWindowListener(new WindowAdapter() {
            public void windowClosing(WindowEvent e) {
                System.exit(0);
            }
        });
        
        setVisible(true);
    }
    
    private void setupDisplay() {
        display.setBounds(30, 40, 250, 40);
        display.setBackground(Color.BLACK);
        display.setForeground(Color.WHITE);
        display.setFont(new Font("Monospaced", Font.BOLD, 20));
        display.setEditable(false);
        add(display);
        
        memLabel.setBounds(30, 90, 40, 25);
        memLabel.setForeground(Color.RED);
        add(memLabel);
    }
    
    private void setupButtons() {
        int startX = 30, startY = 130;
        int btnW = 55, btnH = 35;
        int gap = 5;
        
        // Digit buttons (4x3 grid)
        int digitX = startX;
        int digitY = startY;
        for (int i = 0; i < digitText.length; i++) {
            Button btn = createButton(digitText[i], digitX, digitY, btnW, btnH);
            digitX += btnW + gap;
            if ((i + 1) % 3 == 0) {
                digitX = startX;
                digitY += btnH + gap;
            }
        }
        
        // Operator buttons
        int opX = startX + 3 * (btnW + gap) + 10;
        int opY = startY;
        for (int i = 0; i < operatorText.length; i++) {
            Button btn = createButton(operatorText[i], opX, opY, btnW, btnH);
            btn.setForeground(Color.RED);
            opY += btnH + gap;
            if (i == 3) opY = startY + 2 * (btnH + gap);
        }
        
        // Memory buttons (vertical column)
        int memX = startX;
        int memY = startY + 4 * (btnH + gap);
        for (int i = 0; i < memoryText.length; i++) {
            Button btn = createButton(memoryText[i], memX, memY, btnW, btnH);
            btn.setForeground(Color.BLUE);
            memY += btnH + gap;
        }
        
        // Special buttons
        int specX = startX + 2 * (btnW + gap);
        int specY = startY + 4 * (btnH + gap);
        for (int i = 0; i < specialText.length; i++) {
            Button btn = createButton(specialText[i], specX, specY, btnW * 2, btnH);
            btn.setForeground(Color.RED);
            specX += btnW * 2 + gap;
        }
    }
    
    private Button createButton(String label, int x, int y, int w, int h) {
        Button btn = new Button(label);
        btn.setBounds(x, y, w, h);
        btn.addActionListener(this);
        add(btn);
        return btn;
    }
    
    public void actionPerformed(ActionEvent e) {
        String cmd = e.getActionCommand();
        
        if (isDigit(cmd)) {
            handleDigit(cmd);
        } else if (cmd.equals(".")) {
            handleDecimal();
        } else if (cmd.equals("+/-")) {
            handleSign();
        } else if (isOperator(cmd)) {
            handleOperator(cmd);
        } else if (cmd.equals("=")) {
            calculateResult();
        } else if (cmd.equals("sqrt")) {
            handleSqrt();
        } else if (cmd.equals("1/X")) {
            handleReciprocal();
        } else if (cmd.startsWith("M")) {
            handleMemory(cmd);
        } else if (cmd.equals("Back")) {
            handleBackspace();
        } else if (cmd.equals("C")) {
            handleClear();
        } else if (cmd.equals("CE")) {
            handleClearEntry();
        }
    }
    
    private boolean isDigit(String s) {
        return s.length() == 1 && s.charAt(0) >= '0' && s.charAt(0) <= '9';
    }
    
    private boolean isOperator(String s) {
        return s.equals("+") || s.equals("-") || s.equals("*") || s.equals("/") || s.equals("%");
    }
    
    private void handleDigit(String digit) {
        if (newNumber) {
            display.setText(digit);
            newNumber = false;
        } else {
            display.setText(display.getText() + digit);
        }
    }
    
    private void handleDecimal() {
        if (!display.getText().contains(".")) {
            display.setText(display.getText() + ".");
            newNumber = false;
        }
    }
    
    private void handleSign() {
        double val = Double.parseDouble(display.getText());
        display.setText(formatNumber(-val));
    }
    
    private void handleOperator(String op) {
        firstNumber = Double.parseDouble(display.getText());
        operator = op.charAt(0);
        newNumber = true;
    }
    
    private void calculateResult() {
        double second = Double.parseDouble(display.getText());
        double result = 0;
        
        switch (operator) {
            case '+': result = firstNumber + second; break;
            case '-': result = firstNumber - second; break;
            case '*': result = firstNumber * second; break;
            case '/': 
                if (second != 0) result = firstNumber / second;
                else { display.setText("Error"); return; }
                break;
            case '%':
                if (second != 0) result = firstNumber % second;
                else { display.setText("Error"); return; }
                break;
            default: result = second;
        }
        
        display.setText(formatNumber(result));
        newNumber = true;
    }
    
    private void handleSqrt() {
        double val = Double.parseDouble(display.getText());
        if (val >= 0) {
            display.setText(formatNumber(Math.sqrt(val)));
        } else {
            display.setText("Error");
        }
        newNumber = true;
    }
    
    private void handleReciprocal() {
        double val = Double.parseDouble(display.getText());
        if (val != 0) {
            display.setText(formatNumber(1.0 / val));
        } else {
            display.setText("Error");
        }
        newNumber = true;
    }
    
    private void handleMemory(String cmd) {
        double val = Double.parseDouble(display.getText());
        
        switch (cmd) {
            case "MC":
                memory = 0;
                memLabel.setText(" ");
                break;
            case "MR":
                display.setText(formatNumber(memory));
                newNumber = true;
                break;
            case "MS":
                memory = val;
                memLabel.setText("M");
                break;
            case "M+":
                memory += val;
                memLabel.setText("M");
                break;
        }
    }
    
    private void handleBackspace() {
        String text = display.getText();
        if (text.length() > 1) {
            display.setText(text.substring(0, text.length() - 1));
        } else {
            display.setText("0");
            newNumber = true;
        }
    }
    
    private void handleClear() {
        firstNumber = 0;
        operator = ' ';
        memory = 0;
        memLabel.setText(" ");
        handleClearEntry();
    }
    
    private void handleClearEntry() {
        display.setText("0");
        newNumber = true;
    }
    
    private String formatNumber(double num) {
        if (num == (long) num) {
            return String.valueOf((long) num);
        }
        // Round to 10 decimal places to avoid floating point issues
        return String.format("%.10f", num).replaceAll("0*$", "").replaceAll("\\.$", "");
    }
    
    public static void main(String[] args) {
        new SimpleCalc();
    }
}