# LexmoAI API (FastAPI)

This is the base version of the **LexmoAI API**, built with **FastAPI**. It provides a foundational API key authentication system with public and protected routes, along with admin controls to create, manage, and revoke API keys. This structure will serve as the groundwork for further feature development.

---

## Features

- **Public Endpoint**: Accessible without authentication for checking if API is live or down.
- **Secure Endpoint**: Requires a valid API key.
- **Admin Endpoints**: For creating, listing, and deleting API keys.
- **Role-based Access Control**: `user` and `admin` roles.
- **Key Metadata**: Tracks owner, role, activation status, timestamps, and last usage.

---


## Project Structure

```bash
LexmoAI_API/
├── app/                          
│   ├── main.py              # Entry point for the FastAPI application
│   ├── limiter.py           # Rate limiting logic
│   ├── db.py                # Database connection and models, using SQLite
│   ├── auth.py              # Authentication logic
│   └── routers/                
│   │   ├── admin.py         # Admin-only routes
│   │   ├── chat.py          # Secure chat routes
│   │   ├── chat_stream.py   # Secure chat streaming routes
│   │   ├── public.py        # Public API routes
│   │   ├── secure.py        # Secure user routes
│   │   └── title.py         # Title generation routes
│   └── services/  
│       ├── Lexmo_chat_stream.py   # Main Lexmo Chat Streaming
│       ├── Lexmo_chat.py    # Main Lexmo Chat 
│       └── Lexmo_title.py   # Main Lexmo Title Generator 
├── scripts/                 
│   ├── create_api_key.py    # Create API key
│   └── list_keys.py         # List all API Keys
├── api_keys_db              # SQLite database 
├── LICENSE/                 # License file (AGPL v3)
├── README.md/               # Repository readme file (this file)
├── .gitignore/              # Git ignore file 
└── requirements.txt         # Python dependencies required for the project
```

---

## Getting Started

### Installation 

1. Clone the repository:

```bash
git clone git@github.com:syncwave-automation/LexmoAI_API.git
cd lexmoai-api
```
2. Create python environment

```bash
python3.11 -m venv "my_env_name"
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

Run the server:
Create .env file and inside that:
```bash
export OPENAI_API_KEY="Your API Key"
```
Then:
```bash
uvicorn app.`main:app --reload
```

---

## API Key Authentication

### Public Endpoint  
**Route**: `GET /api/v1/public/`  
No API key required.

```bash
curl -X GET http://127.0.0.1:8000/api/v1/public/
```
###### Or 

```bash
curl -X GET https://api.lexmo.in/api/v1/public/
```
**Success Response**:
```json
{
  "message": "Hello from the public route!"
}
```

---

### Secure Endpoint  
**Route**: `GET /api/v1/secure/`  
Requires a valid API key in the `X-API-Key` header.

```bash
curl -X GET http://127.0.0.1:8000/api/v1/secure/ \
  -H "X-API-Key: your_user_api_key_here"
```
###### Or 
```bash
curl -X GET https://api.lexmo.in/api/v1/secure/ \
  -H "X-API-Key: your_user_api_key_here"
```


**Success Response**:
```json
{
  "message": "You have accessed a protected endpoint!",
  "user": {
    "id": 1,
    "owner": "TestUser",
    "role": "user"
  }
}
```

**Unauthorized Response**:
```json
{"detail":"Invalid or inactive API key"}
```
### Title Endpoint  
**Route**: `GET /api/v1/secure/title`  
Requires a valid API key in the `X-API-Key` header.

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/secure/title" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: <VALID_USER_KEY>" \
     -d '{"query": "Your legal question here"}'

```
###### Or 
```bash
curl -X POST "https://api.lexmo.in/api/v1/secure/chat" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: <VALID_USER_KEY>" \
     -d '{"query": "Your legal question here"}'

```

**Success Response**:
```json
{
  "title": "YOUR TITLE"
}

```

**Unauthorized Response**:
```json
{"detail":"Invalid or inactive API key"}
```

### Chat Endpoint  
#### Chat response
**Route**: `GET /api/v1/secure/chat`  
Requires a valid API key in the `X-API-Key` header.

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/secure/chat" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: <VALID_USER_KEY>" \
     -d '{"query": "Your legal question here"}'

```
###### Or 
```bash
curl -X POST "https://api.lexmo.in/api/v1/secure/chat" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: <VALID_USER_KEY>" \
     -d '{"query": "Your legal question here"}'

```

**Success Response**:
```json
{
  "retrieved_files": [
    {
      "store_name": "State_Acts",
      "filename": "SomeAct.pdf",
      "content": [
        "... text snippet ...",
        "... more text snippet ..."
      ],
      "score": 0.89
    },
    {
      "store_name": "Union_Acts",
      "filename": "SomeOtherAct.pdf",
      "content": [
        "... text snippet ..."
      ],
      "score": 0.78
    }
  ],
  "final_answer": "Hello, I'm Lexmo. Here's the best possible legal advice..."
}

```

**Unauthorized Response**:
```json
{"detail":"Invalid or inactive API key"}
```
#### Chat rsponse streaming

**Route**: `WS /api/v1/secure/chat_stream`  

***Testing***

To test locally, you could use a tool like wscat:
```bash
npm install -g wscat
```
```bash
wscat -c "ws://127.0.0.1:8000/api/v1/secure/chat_stream?api_key=YOUR_VALID_KEY"
```
###### Or 
```bash
wscat -c "https://api.lexmo.in/api/v1/secure/chat_stream?api_key=YOUR_VALID_KEY"
```

Then:
```bash
> { "query": "Your Query" }

```

---

## Admin Endpoints

### Create New API Key  
**Route**: `POST /api/v1/admin/create_key`  
Requires an admin API key.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/admin/create_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_admin_api_key_here" \
  -d '{"owner":"TestUser","role":"user/admin"}'
```
###### Or 
```bash
curl -X GET https://api.lexmo.in/api/v1/admin/create_key\
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_admin_api_key_here" \
  -d '{"owner":"TestUser","role":"user/admin"}'
```

**Response**:
```json
{
  "message": "API Key created successfully",
  "api_key": "the-raw-key-just-created",
  "owner": "TestUser",
  "role": "user"
}
```

---

### List All API Keys  
**Route**: `GET /api/v1/admin/list_keys/`  
Requires an admin API key.

```bash
curl -H "X-API-Key: your_admin_api_key_here" \
  http://127.0.0.1:8000/api/v1/admin/list_keys/
```
###### Or 
```bash
curl -X GET https://api.lexmo.in/api/v1/admin/list_keys/ \
  -H "X-API-Key: your_user_api_key_here"
```

**Response**:
```json
[
  {
    "id": 1,
    "owner": "Alice",
    "role": "admin",
    "active": true,
    "created_at": "2025-03-31T10:10:00",
    "last_used_at": null
  },
  ...
]
```

---

### Delete an API Key  
**Route**: `DELETE /api/v1/admin/delete_key/{owner}`  
Requires an admin API key.

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/admin/delete_key/TestUser \
  -H "X-API-Key: your_admin_api_key_here"
```
###### Or 
```bash
curl -X GET https://api.lexmo.in/api/v1/admin/delete_key/TestUser \
  -H "X-API-Key: your_user_api_key_here"
```

**Success Response**:
```json
{"message": "Deleted API key for owner: TestUser"}
```

**Error Response**:
```json
{"detail": "No API key found for owner: TestUser"}
```

---

## Notes

- This is **not the final version**.
- Designed to be lightweight, secure, and extendable.

---

## License

Distributed under the AGPL-3.0 License. Check [LICENSE](https://github.com/syncwave-automation/LexmoAI_API/blob/main/LICENSE) 
for additional information.
