var builder = WebApplication.CreateBuilder(args);

// 1. Add CORS so Next.js (port 3000) can talk to .NET
builder.Services.AddCors(options => {
    options.AddPolicy("NextJsPolicy", policy => {
        policy.WithOrigins("http://localhost:3000")
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

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
            Console.WriteLine($"Received from Button: {message}");

            if (message == "sendImage") //Checking the type of request.
            {
                string imagePath = "samurai.png";

                if (File.Exists(imagePath))
                {
                    byte[] imageBytes = await File.ReadAllBytesAsync(imagePath);
                    string base64Image = Convert.ToBase64String(imageBytes);

                    var payload = new
                    {
                        type = "image",
                        format = "image/jpeg",
                        data = base64Image
                    };

                    string json = System.Text.Json.JsonSerializer.Serialize(payload);
                    byte[] responseBuffer = System.Text.Encoding.UTF8.GetBytes(json);

                    await webSocket.SendAsync(
                        new ArraySegment<byte>(responseBuffer),
                        System.Net.WebSockets.WebSocketMessageType.Text,
                        true,
                        CancellationToken.None
                    );

                    Console.WriteLine("Sent image to frontend");
                }
                else
                {
                    var payload = new
                    {
                        type = "text",
                        message = "test.jpg not found in backend folder"
                    };

                    string json = System.Text.Json.JsonSerializer.Serialize(payload);
                    byte[] responseBuffer = System.Text.Encoding.UTF8.GetBytes(json);

                    await webSocket.SendAsync(
                        new ArraySegment<byte>(responseBuffer),
                        System.Net.WebSockets.WebSocketMessageType.Text,
                        true,
                        CancellationToken.None
                    );
                }
            }
            else
            {
                var payload = new
                {
                    type = "text",
                    message = "A regular message from backend!"
                };

                string json = System.Text.Json.JsonSerializer.Serialize(payload);
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