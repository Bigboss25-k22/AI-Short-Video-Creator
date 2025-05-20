
# Video Script Generator API

This API generates video scripts using OpenAI's GPT-4 model based on user prompts.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file in the root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
PORT=3000
```

3. Start the server:
```bash
# Development mode
npm run dev

# Production mode
npm start
```

## API Endpoints

### Generate Video Script
- **URL**: `/api/generate-script`
- **Method**: `POST`
- **Body**:
```json
{
  "prompt": "Your video script prompt here"
}
```
- **Response**:
```json
{
  "script": "Generated video script content"
}
```

### Health Check
- **URL**: `/health`
- **Method**: `GET`
- **Response**:
```json
{
  "status": "OK"
}
```

## Example Usage

```javascript
// Using fetch
const response = await fetch('http://localhost:3000/api/generate-script', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    prompt: "Create a script for a 1-minute product demonstration video for a new smartphone"
  })
});

const data = await response.json();
console.log(data.script);
```

## Error Handling

The API returns appropriate error messages with status codes:
- 400: Bad Request (missing prompt)
- 500: Internal Server Error (OpenAI API issues) 



