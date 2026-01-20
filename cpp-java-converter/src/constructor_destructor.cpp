class FileHandler {
private:
    char* filename;

public:
    FileHandler(const char* name) {
        filename = new char[strlen(name) + 1];
        strcpy(filename, name);
    }

    ~FileHandler() {
        delete[] filename;
    }

    void open() { /* ... */ }
};