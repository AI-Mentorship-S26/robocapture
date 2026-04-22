using System.Net.WebSockets;
using System.Text.Json;

System.Net.WebSockets.WebSocket? frontendSocket = null;


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

var piUri = new Uri(piUrl);
var persistentPiSocket = new ClientWebSocket();

async Task SendStatusToFrontend(bool piConnected) {
    if (frontendSocket == null || frontendSocket.State != WebSocketState.Open) return;
    var status = JsonSerializer.Serialize(new { type = "pi_status", connected = piConnected });
    var bytes = System.Text.Encoding.UTF8.GetBytes(status);
    try {
        await frontendSocket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);
    } catch { }
}

// Connect to Pi and listen for autonomous images
_ = Task.Run(async () => {
    bool wasPiConnected = false;
    while (true) {
        try {
            if (persistentPiSocket.State != WebSocketState.Open) {
                persistentPiSocket = new ClientWebSocket();
                await persistentPiSocket.ConnectAsync(piUri, CancellationToken.None);
                Console.WriteLine("Persistent Pi connection established!");
                wasPiConnected = true;
                await SendStatusToFrontend(true);
            }

            var buffer = new byte[1024 * 1024 * 5]; // 5MB
            var result = await persistentPiSocket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
            string message = System.Text.Encoding.UTF8.GetString(buffer, 0, result.Count);

            // Forward to frontend if we have a connected frontend socket
            if (frontendSocket != null && frontendSocket.State == WebSocketState.Open) {
                byte[] responseBuffer = System.Text.Encoding.UTF8.GetBytes(message);
                await frontendSocket.SendAsync(new ArraySegment<byte>(responseBuffer), WebSocketMessageType.Text, true, CancellationToken.None);
            }
        } catch (Exception ex) {
            Console.WriteLine($"Pi connection error: {ex.Message} — retrying in 2s");
            if (wasPiConnected) {
                wasPiConnected = false;
                await SendStatusToFrontend(false);
            }
            await Task.Delay(2000);
        }
    }
});

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
    frontendSocket = webSocket;
    var buffer = new byte[1024 * 4];
    while (webSocket.State == System.Net.WebSockets.WebSocketState.Open) {
        var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
        if (result.MessageType == System.Net.WebSockets.WebSocketMessageType.Close) {
            await webSocket.CloseAsync(System.Net.WebSockets.WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
        } else {
            var message = System.Text.Encoding.UTF8.GetString(buffer, 0, result.Count);
            Console.WriteLine($"Received from frontend: {message}");

            if (message == "captureImage") {
                await SendToPiPersistent("captureImage");
                // Response comes back through the persistent listener automatically
            } else if (message.StartsWith("reward:") || 
                    message.StartsWith("punishment:") || 
                    message.StartsWith("setModel:") ||
                    message.StartsWith("datasetLabel:") ||
                    message.StartsWith("datasetSkip:") ||
                    message == "captureDatasetImage" ||
                    message == "startNavigation") {
                await SendToPiPersistent(message);
            } else {
                var payload = new { type = "text", message = "A regular message from backend!" };
                string json = JsonSerializer.Serialize(payload);
                byte[] responseBuffer = System.Text.Encoding.UTF8.GetBytes(json);
                await webSocket.SendAsync(
                    new ArraySegment<byte>(responseBuffer),
                    System.Net.WebSockets.WebSocketMessageType.Text,
                    true,
                    CancellationToken.None
                );
            }
        }
    }
}

async Task SendToPiPersistent(string message) {
    try {
        byte[] buffer = System.Text.Encoding.UTF8.GetBytes(message);
        await persistentPiSocket.SendAsync(
            new ArraySegment<byte>(buffer),
            WebSocketMessageType.Text,
            true,
            CancellationToken.None
        );
    } catch (Exception ex) {
        Console.WriteLine($"Error sending to Pi: {ex.Message}");
    }
}
