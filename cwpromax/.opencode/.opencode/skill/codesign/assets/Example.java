// Example Java file for Co-De Sign API testing
public class Example {
    private String message;
    
    public Example(String message) {
        this.message = message;
    }
    
    public String getMessage() {
        return message;
    }
    
    public void setMessage(String message) {
        this.message = message;
    }
    
    public void printMessage() {
        System.out.println("Message: " + message);
    }
    
    public static void main(String[] args) {
        Example example = new Example("Hello from Co-De Sign!");
        example.printMessage();
    }
}
