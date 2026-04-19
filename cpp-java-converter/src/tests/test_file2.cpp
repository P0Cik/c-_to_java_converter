class ArrayProcessor {
private:
    int size;
    int currentIndex;
    
public:
    ArrayProcessor(int s) {
        size = s;
        currentIndex = 0;
    }
    
    void processArray() {
        int i = 0;
        
        // For loop
        for (i = 0; i < size; i = i + 1) {
            std::cout << "Processing index: " << i;
        }
        
        // While loop
        int count = 0;
        while (count < 5) {
            std::cout << "Count: " << count;
            count = count + 1;
        }
        
        // Do-while loop
        int attempts = 0;
        do {
            std::cout << "Attempt: " << attempts;
            attempts = attempts + 1;
        } while (attempts < 3);
    }
    
    void findValue(int target) {
        int values[5];
        values[0] = 10;
        values[1] = 20;
        values[2] = 30;
        values[3] = 40;
        values[4] = 50;
        
        int i = 0;
        bool found = false;
        
        while (i < 5 && !found) {
            if (values[i] == target) {
                found = true;
                std::cout << "Value found at index: " << i;
            }
            i = i + 1;
        }
        
        if (!found) {
            std::cout << "Value not found";
        }
    }
    
    int calculateSum() {
        int sum = 0;
        int i = 1;
        
        for (i = 1; i <= 10; i = i + 1) {
            sum = sum + i;
        }
        
        return sum;
    }
    
    void printPattern(int rows) {
        int i = 1;
        
        while (i <= rows) {
            int j = 1;
            std::string line = "";
            
            while (j <= i) {
                line = line + "*";
                j = j + 1;
            }
            
            std::cout << line;
            i = i + 1;
        }
    }
};

int main() {
    ArrayProcessor processor(10);
    
    processor.processArray();
    processor.findValue(30);
    
    int sum = processor.calculateSum();
    std::cout << "Sum: " << sum;
    
    processor.printPattern(5);
    
    return 0;
}