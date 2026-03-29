import { NextResponse } from 'next/server';
import { writeFile, unlink } from 'fs/promises';
import { join } from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import os from 'os';

const execAsync = promisify(exec);

export async function POST(request: Request) {
  let tempFilePath = "";
  try {
    const formData = await request.formData();
    const file = formData.get('image') as File;
    const userId = formData.get('userId') as string || 'anonymous';

    if (!file) {
      return NextResponse.json({ error: "No image file provided." }, { status: 400 });
    }

    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Save to temp directory
    tempFilePath = join(os.tmpdir(), `${Date.now()}-${file.name.replace(/[^a-zA-Z0-9.-]/g, '_')}`);
    await writeFile(tempFilePath, buffer);

    // Provide the path to the Python environment and script
    // Note: Assuming a standard project layout where Next.js is in /frontend and the Python is in the root
    const pythonExecutable = join(process.cwd(), '../.venv/Scripts/python.exe');
    const pythonScript = join(process.cwd(), '../image_to_vector.py');

    // Run the python script from the root workspace folder to ensure it finds the root .env
    const command = `"${pythonExecutable}" "${pythonScript}" "${tempFilePath}" "${userId}"`;
    
    const { stdout, stderr } = await execAsync(command, {
        cwd: join(process.cwd(), '..')
    });

    try {
        // Find the JSON block in the stdout in case Python printed warnings before it
        const jsonMatch = stdout.match(/\{[\s\S]*\}/);
        if (!jsonMatch) throw new Error("No JSON returned from Python script");

        const result = JSON.parse(jsonMatch[0]);

        if (result.success) {
            return NextResponse.json(result);
        } else {
            return NextResponse.json({ error: result.error || "Python script failed", stderr, stdout }, { status: 500 });
        }
    } catch (parseError) {
       console.error("Failed to parse Python output:", stdout, stderr);
       return NextResponse.json({ error: "Failed to parse vectorizer output", stdout, stderr }, { status: 500 });
    }

  } catch (error: any) {
    console.error("Vectorization Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    // CRITICAL: Clean up the temporary file to prevent disk-space leaks
    if (tempFilePath) {
      try {
        await unlink(tempFilePath);
      } catch (cleanupError) {
        console.error(`Failed to clean up temp file ${tempFilePath}:`, cleanupError);
      }
    }
  }
}
