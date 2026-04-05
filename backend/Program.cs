using System.Net.WebSockets;
using System.Text.Json;
var builder = WebApplication.CreateBuilder(args);

// 1. Add CORS so Next.js (port 3000) can talk to .NET
builder.Services.AddCors(options => {
    options.AddPolicy("NextJsPolicy", policy => {
        policy.WithOrigins("http://localhost:3000")
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

var piUrl = builder.Configuration["PiWebSocketUrl"] ?? "ws://172.20.10.12:8765";

var app = builder.Build();

app.UseCors("NextJsPolicy");
app.UseWebSockets(); // This enables the WebSocket protocol

// 2. The WebSocket "Endpoint"
app.Map("/ws", async context => {
    if (context.WebSockets.IsWebSocketRequest) {
        using var webSocket = await context.WebSockets.AcceptWebSocketAsync();
        Console.WriteLine("Next.js connected!");
        
        await EchoLoop(webSocket);
    } else {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
    }
});

app.Run();

// 3. The Message Handler
async Task EchoLoop(System.Net.WebSockets.WebSocket webSocket) {
    var buffer = new byte[1024 * 4];
    while (webSocket.State == System.Net.WebSockets.WebSocketState.Open) {
        var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
        if (result.MessageType == System.Net.WebSockets.WebSocketMessageType.Close) {
            await webSocket.CloseAsync(System.Net.WebSockets.WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
        } else {
            var message = System.Text.Encoding.UTF8.GetString(buffer, 0, result.Count);
            Console.WriteLine($"Received from frontend: {message}");

            if (message == "captureImage") {
                var piResponse = await GetImageFromPi(piUrl);

                byte[] responseBuffer = System.Text.Encoding.UTF8.GetBytes(piResponse);
                await webSocket.SendAsync(
                    new ArraySegment<byte>(responseBuffer),
                    System.Net.WebSockets.WebSocketMessageType.Text,
                    true,
                    CancellationToken.None
                );
            } else if (message.StartsWith("reward:") || 
                    message.StartsWith("punishment:") || 
                    message.StartsWith("setModel:")) {
                // Forward directly to Pi without any processing
                await ForwardToPi(piUrl, message);
            } else {
                var payload = new { type = "text", message = "A regular message from backend!" };
                string json = JsonSerializer.Serialize(payload);
                byte[] responseBuffer = System.Text.Encoding.UTF8.GetBytes(json);
                await webSocket.SendAsync(
                    new ArraySegment<byte>(responseBuffer),
                    System.Net.WebSoc   kets.WebSocketMessageType.Text,
                    true,
                    CancellationToken.None
                );
            }
        }
    }
}

async Task<string> GetImageFromPi(string piUrl) {
    //var piUri = new Uri("ws://172.20.10.12:8765"); // Use Pi's IP
    var piUri = new Uri(piUrl);
    using var piSocket = new ClientWebSocket();
    
    try {
        await piSocket.ConnectAsync(piUri, CancellationToken.None);
        Console.WriteLine("Connected to Pi WebSocket server!");

        // Send capture command
        byte[] commandBuffer = System.Text.Encoding.UTF8.GetBytes("captureImage");
        await piSocket.SendAsync(
            new ArraySegment<byte>(commandBuffer),
            System.Net.WebSockets.WebSocketMessageType.Text,
            true,
            CancellationToken.None
        );

        // Receive image — use large buffer since images are big
        var receiveBuffer = new byte[1024 * 1024 * 5]; // 5MB
        var receiveResult = await piSocket.ReceiveAsync(new ArraySegment<byte>(receiveBuffer), CancellationToken.None);
        string piResponse = System.Text.Encoding.UTF8.GetString(receiveBuffer, 0, receiveResult.Count);

        await piSocket.CloseAsync(System.Net.WebSockets.WebSocketCloseStatus.NormalClosure, "Done", CancellationToken.None);
        return piResponse;

    } catch (Exception ex) {
        Console.WriteLine($"Error connecting to Pi: {ex.Message}");
        var error = new { type = "text", message = $"Pi connection failed: {ex.Message}" };
        return JsonSerializer.Serialize(error);
    }
}

async Task ForwardToPi(string piUrl, string message) {
    var piUri = new Uri(piUrl);
    using var piSocket = new ClientWebSocket();

    try {
        await piSocket.ConnectAsync(piUri, CancellationToken.None);

        byte[] commandBuffer = System.Text.Encoding.UTF8.GetBytes(message);
        await piSocket.SendAsync(
            new ArraySegment<byte>(commandBuffer),
            System.Net.WebSockets.WebSocketMessageType.Text,
            true,
            CancellationToken.None
        );

        await piSocket.CloseAsync(System.Net.WebSockets.WebSocketCloseStatus.NormalClosure, "Done", CancellationToken.None);
        Console.WriteLine($"Forwarded to Pi: {message}");

    } catch (Exception ex) {
        Console.WriteLine($"Error forwarding to Pi: {ex.Message}");
    }
}