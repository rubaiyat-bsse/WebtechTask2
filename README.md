# Bookshelf: Library Backend with FastAPI

CSE 3102L Web Technology Lab, Topic 04: Backend Frameworks and Architecture.

This is a fresh implementation directly inside `task2/`. It implements two features:

1. **Book catalogue and inventory:** create, read, list, update and delete books; borrow and return copies.
2. **Member directory:** create, read, list, update and delete library members; prevent duplicate email addresses.

Both resources have a complete CRUD lifecycle. CRUD means **Create, Read, Update, Delete**. Borrowing adds the slide's example of an operation that can fail because of a business rule.

The layout follows the professor's four layers: **handler -> service -> repository**, with **domain objects containing rules**. It also includes environment configuration, dependency injection, centralized errors, request IDs, request/service logs, persistent SQLite storage, and automated tests.

## 1. Start here

Requirements: **Python 3.11 or later**, including `venv`, `pip`, and `sqlite3`. The locked dependencies and all tests were verified on Linux with Python 3.14.4.

Open a terminal in the directory containing this README, `task2/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.txt
cp .env.example .env
set -a
source .env
set +a
python run.py
```

Open [Swagger UI](http://127.0.0.1:8000/docs) to inspect and try the endpoints.

Other useful URLs:

- [Health check](http://127.0.0.1:8000/health)
- [OpenAPI specification](http://127.0.0.1:8000/openapi.json)

Stop the server with `Ctrl+C`. Development auto-reload is optional:

```bash
python -m uvicorn run:app --reload --host 127.0.0.1 --port 8000
```

**Run all automated tests in a second terminal:**

```bash
# From task2/
source .venv/bin/activate
python -m pytest -q
```

Verified result:

```text
60 passed
```

The tests start the application themselves. No separate server, Postman, database service, or internet connection is required to run them after dependencies are installed.

## 2. How this matches the assignment and slides

The lab requirements on slides 24-25 and the layout on slides 27-30 guide this implementation.

| Requirement | Implementation |
| --- | --- |
| Preferred framework | FastAPI; Uvicorn runs the HTTP server |
| Library domain, two resources | Books and Members |
| Full CRUD lifecycle | POST, GET one, GET list, PUT, DELETE for both resources |
| Separate handlers, services, repositories, domain | Separate folders under `app/` |
| No SQL or business rules in handlers | Handlers only call services and set HTTP responses |
| Dependencies passed in; wired in one place | `create_app()` in `app/__init__.py` |
| Business rule can fail with 409 | Borrow unavailable stock; return excess stock; duplicate member email |
| Field-level validation with 422 | Pydantic input models plus domain validation |
| Correct status codes and Location | 201 + Location on creation; 200 for reads/updates; 204 for deletion |
| One error format | RFC 9457 Problem Details, `application/problem+json` |
| Request ID, request and service logs | Middleware and `logging_context.py` |
| Environment settings and example | `config.py`, `.env.example`; `.env` ignored |
| Declared and locked dependencies | `requirements.in` and hash-locked `requirements.txt` |
| Five or more tests, including failure paths | 60 tests: 50 integration cases and 10 unit cases |
| Automatically do what Postman would do | HTTP integration tests exercise real routes and SQLite |
| Architecture explanation and AI disclosure | Sections below |

The slide's single `copies` counter is expressed as **total_copies** and **available_copies** here. The extra distinction lets return and update operations enforce correct inventory rules. The folder responsibilities and borrow/return URLs follow the slide's approach.

## 3. Why FastAPI, SQLite and pytest?

**FastAPI** maps an HTTP method and URL to a Python function. It handles routing, reads JSON, validates typed input using Pydantic, and generates interactive API documentation. We supply the application's rules and architecture. Its dependency system supplies services to handlers. See the official [dependency tutorial](https://fastapi.tiangolo.com/tutorial/dependencies/).

**Uvicorn** is the server process that listens on port 8000 and passes HTTP requests to FastAPI. FastAPI is the application framework; Uvicorn handles the network-facing server.

**SQLite** stores records in a local file. Unlike a Python dictionary, it retains data when the server restarts. Unlike PostgreSQL, it needs no separately installed database service, credentials, or container. Python already provides the driver. SQL is short and visible, so this lab does not add an ORM, a library that maps database rows to objects. See [Python's sqlite3 documentation](https://docs.python.org/3.14/library/sqlite3.html).

**pytest** discovers functions named `test_...`, runs them, and checks their assertions. FastAPI's `TestClient` sends HTTP-style requests into the application. The pinned Starlette version uses **HTTPX2**, so `httpx2` is declared as the test transport dependency. See [FastAPI's testing guide](https://fastapi.tiangolo.com/tutorial/testing/).

## 4. Project structure

```text
task2/
├── app/
│   ├── __init__.py              # create_app: wiring, middleware, error handlers
│   ├── config.py                # environment settings and startup validation
│   ├── errors.py                # application exceptions, independent of HTTP
│   ├── dependencies.py          # FastAPI Depends providers
│   ├── schemas.py               # request/response models and documented errors
│   ├── logging_context.py       # per-request ID and log formatting
│   ├── domain/
│   │   ├── book.py              # inventory rules
│   │   └── member.py            # member validation and normalization
│   ├── repositories/
│   │   ├── database.py          # schema creation, transactions, connection cleanup
│   │   ├── book_repository.py   # book SQL and row conversion
│   │   └── member_repository.py # member SQL and row conversion
│   ├── services/
│   │   ├── ports.py             # storage interfaces and transaction contract
│   │   ├── book_service.py      # book use cases
│   │   └── member_service.py    # member use cases
│   └── routes/
│       ├── books.py             # thin book controllers
│       └── members.py           # thin member controllers
├── tests/
│   ├── conftest.py              # isolated application/database fixtures
│   ├── test_books.py            # book CRUD, rules and failure cases
│   ├── test_members.py          # member CRUD, uniqueness and validation
│   ├── test_http.py             # errors, request IDs, logs and documentation
│   ├── test_storage.py          # persistence, rollback and concurrent borrowing
│   └── test_domain.py           # domain/service tests without HTTP
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.in              # direct dependencies
├── requirements.txt             # exact versions, transitive dependencies, hashes
├── run.py
└── README.md
```

Package directories also contain `__init__.py`. Python uses these to identify importable packages. The runtime creates `data/library.sqlite3`; it is intentionally ignored by Git.

## 5. The four layers, intuitively

### Handler / controller: translate HTTP

Files: `app/routes/books.py`, `app/routes/members.py`.

A handler receives a validated request, calls a service method and returns the result. It knows about HTTP details such as the `Location` header and status 204. It does not execute SQL or decide whether a book can be borrowed.

For example, the borrow handler essentially does:

```python
return service.borrow_book(book_id)
```

### Service: carry out a use case

Files: `app/services/book_service.py`, `member_service.py`.

A service coordinates the work: open a transaction, load a record, check that it exists, ask the domain object to apply a rule, save it, then log success after commit.

It does not read an HTTP request, build JSON, or choose status codes. A script or a test can call it directly.

The member service checks email uniqueness because that rule needs access to other member records. A single `Member` object cannot know which other members exist.

### Domain: the meaning and rules of the data

Files: `app/domain/book.py`, `member.py`.

These are ordinary Python dataclasses. A dataclass is a convenient way to define an object whose main job is to hold named fields.

`Book.borrow()` rejects a borrow when no copy is available. `Book.give_back()` rejects a return when all copies are already present. These rules make sense even if the interface later becomes a command-line program.

The domain imports neither FastAPI nor SQLite.

### Repository: store and retrieve objects

Files: `app/repositories/`.

A repository converts database rows into domain objects and vice versa. For example, `get(book_id)` returns a `Book` or `None`.

Queries use `?` placeholders with separate values. Submitted titles and email addresses are data, never SQL syntax. Repositories do not decide whether a borrow is allowed.

### Why this separation helps

If everything were inside a route, testing a borrowing rule would require HTTP setup and storage setup. Here the rule can be tested with a plain `Book` instance. Replacing SQLite requires a new repository/transaction implementation and wiring it in `create_app()`; routes and business rules can stay unchanged.

## 6. Dependency injection and transactions

**Dependency injection** means passing an object the collaborators it needs rather than constructing them inside the object. It is similar to passing a C++ function an interface reference rather than hard-coding a concrete class.

`create_app()` is the **composition root**, the one place that chooses concrete implementations:

1. Read and validate configuration.
2. Initialize the SQLite database.
3. Define `unit_of_work()`, which creates repositories sharing a transaction.
4. Pass that function to the services.
5. Store the services on `app.state`.
6. Register routes, handlers and middleware.

FastAPI's `Depends` providers fetch those services for each handler.

A **Protocol** in `services/ports.py` describes the methods a repository must support. It plays a role similar to an interface; a compatible object does not have to inherit from it.

A **unit of work** groups the database operations for one use case into one transaction:

```python
with self.unit_of_work() as repos:
    book = self._require(repos.books, book_id)
    book.borrow()
    repos.books.save(book)
```

The block commits if it finishes normally. An exception rolls back all its changes. The connection closes in either case. Commit happens before the service returns, so a commit failure cannot accidentally produce a success response.

`BEGIN IMMEDIATE` reserves SQLite's write lock **before reading**. Without that protection, two requests could both see one available copy, both decrement to zero and both report success. With it, the second request reads the first request's committed state and fails with 409.

For simplicity, even read use cases use this transaction wrapper. That serializes database access more than necessary. It is a deliberate small-lab tradeoff, and the concurrent-borrow test checks correctness across two app instances sharing one database file.

## 7. Data and business rules

### Books

A create or full-update body:

```json
{
  "title": "Clean Architecture",
  "author": "Robert C. Martin",
  "total_copies": 2
}
```

A response adds server-controlled fields:

```json
{
  "id": 1,
  "title": "Clean Architecture",
  "author": "Robert C. Martin",
  "total_copies": 2,
  "available_copies": 2
}
```

Rules:

- Title: 1-200 characters after trimming.
- Author: 1-120 characters after trimming.
- Total copies: a real JSON integer from 0 through `MAX_COPIES` (default 50).
- Numeric strings such as `"2"`, booleans and fractional counts are rejected.
- Initially, all copies are available.
- Borrowing decreases availability by one; no available stock gives 409.
- Returning increases availability by one; no outstanding borrowed copy gives 409.
- Updating total stock preserves the outstanding borrowed count.
- Total stock cannot be reduced below the borrowed count.
- A book with borrowed copies cannot be deleted.
- Clients cannot directly set `id` or `available_copies`.

Example: total 3, available 1 means 2 copies are borrowed. Updating total to 5 produces available 3. Updating total to 1 fails because 2 copies are still borrowed.

### Members

Create/update body:

```json
{
  "name": "Ayesha Rahman",
  "email": "ayesha@example.com"
}
```

A response adds `id`.

Names contain 1-120 characters after trimming. Email addresses are trimmed, lowercased, limited to 254 characters and checked against a simple `name@domain.suffix` pattern. This is a lab validation rule, not proof that the mailbox exists or a full email-standard validator.

Email addresses are unique regardless of case. Updating a member to their own existing email is allowed; using another member's email gives 409.

Unknown request fields are rejected rather than silently accepted.

## 8. Endpoint reference

`PUT` is a **full replacement of client-editable fields**. Send every field shown above. Server-maintained availability is preserved according to the inventory rules. This project does not implement partial `PATCH` updates.

| Method | Endpoint | Success | Purpose |
| --- | --- | --- | --- |
| POST | /books | 201 + Location | Create a book |
| GET | /books | 200 | List books, ordered by ID |
| GET | /books/{id} | 200 | Read one book |
| PUT | /books/{id} | 200 | Replace title, author and total stock |
| DELETE | /books/{id} | 204, empty body | Delete a book with no outstanding borrows |
| POST | /books/{id}/borrow | 200 | Borrow one copy; no body required |
| POST | /books/{id}/return | 200 | Return one copy; no body required |
| POST | /members | 201 + Location | Create a member |
| GET | /members | 200 | List members, ordered by ID |
| GET | /members/{id} | 200 | Read one member |
| PUT | /members/{id} | 200 | Replace name and email |
| DELETE | /members/{id} | 204, empty body | Delete a member |
| GET | /health | 200 | Application health response |

IDs must be positive integers. Reading or changing a missing resource gives 404. An invalid ID format gives 422. Repeating DELETE after successful deletion gives 404.

`Location: /books/1` tells the client where to read the newly created resource. Collection endpoints return JSON arrays, including `[]` when empty.

## 9. One request through the entire system

Consider `POST /books/1/borrow`:

1. **Uvicorn** receives the HTTP request and invokes FastAPI.
2. **Middleware in** accepts a safe `X-Request-ID` or generates one, then starts timing.
3. **Router and validation** select the borrow handler and validate `book_id`.
4. **Dependency provider** supplies the existing `BookService`.
5. **Service** opens the unit of work and loads the book through its repository.
6. **Domain** runs `book.borrow()`.
7. **Repository/database** save and commit the new availability.
8. **Response model** serializes the returned book into JSON.
9. **Middleware out** adds `X-Request-ID` and logs method, path, status and elapsed time.

If step 5 cannot find the book, `NotFound` becomes 404. If step 6 finds no stock, `Conflict` becomes 409. Either failure exits the transaction without saving. An unexpected exception becomes a generic 500, with its traceback recorded in the server log.

This is the **request lifecycle**. The **CRUD resource lifecycle** is different: create -> read/list -> update -> delete -> verify missing. The integration suite tests both.

## 10. Error handling and validation

Every application-generated HTTP failure uses `Content-Type: application/problem+json`, including malformed JSON, validation, unknown routes, wrong methods, business conflicts and unexpected exceptions.

Example:

```json
{
  "type": "/problems/conflict",
  "title": "Request conflicts with current state",
  "status": 409,
  "detail": "No copies of this book are available",
  "instance": "/books/1/borrow",
  "requestId": "lab-demo-42"
}
```

Validation errors also include field messages:

```json
{
  "type": "/problems/validation_failed",
  "title": "Validation failed",
  "status": 422,
  "detail": "Request fields are invalid",
  "instance": "/books",
  "requestId": "lab-demo-43",
  "errors": [
    {"pointer": "/title", "message": "String should have at least 1 character"}
  ]
}
```

The standard fields follow [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html). `requestId` and `errors` are application extensions. `type` identifies the problem category; its relative URI is an identifier, not an implemented documentation endpoint.

| Failure | HTTP status |
| --- | --- |
| Invalid input or malformed JSON | 422 |
| Missing resource or unknown URL | 404 |
| State/business conflict | 409 |
| Unsupported method | 405, preserving Allow |
| Unexpected exception | 500, generic client detail |

Pydantic checks HTTP input shape/types. Domain validation also runs for direct service calls, so bypassing HTTP does not bypass the core rules. The configurable maximum copies is checked in the domain.

Errors are mapped centrally in `app/__init__.py`, following [FastAPI's custom error-handler pattern](https://fastapi.tiangolo.com/tutorial/handling-errors/). Services raise framework-independent exceptions. Only the HTTP boundary chooses status codes.

The 500 test substitutes a broken service through dependency injection. It asserts that the client sees `Something went wrong` and that the server logs the actual exception exactly once. It adds no debug endpoint to the application.

## 11. Configuration and logging

| Variable | Default | Meaning |
| --- | --- | --- |
| APP_ENV | development | Environment label: development, test or production |
| LOG_LEVEL | INFO | Application logging level |
| MAX_COPIES | 50 | Maximum owned copies per book |
| DATABASE_PATH | task2/data/library.sqlite3 | Persistent SQLite file |

The built-in database default is anchored to the project directory. The example `.env` uses `./data/library.sqlite3`, relative to your working directory, so run its commands from `task2/`.

`.env` is not automatically loaded. The quick-start's `set -a; source .env; set +a` exports it into the process environment without another dependency. Configuration rejects invalid values before startup. Debug mode is disabled.

Every HTTP response gets `X-Request-ID`. A supplied ID is accepted only if it contains 1-64 letters, digits, periods, underscores or hyphens; otherwise a new 12-character ID is generated.

A context variable carries the ID through the request, including its synchronous service calls. Sample log shape:

```text
... INFO app.services.book_service book borrowed id=1 remaining=0 [lab-demo-42]
... INFO app.http POST /books/1/borrow -> 200 duration_ms=1.25 [lab-demo-42]
```

Logs go to standard output. Application request logs omit bodies, email addresses, authorization headers and query strings. Unexpected errors are logged with tracebacks; avoid putting secrets in exception messages.

## 12. How the automated tests replace Postman

In Postman, you send a request, inspect status/headers/body, send another request and check whether the state changed. The tests do exactly that with assertions:

```python
created = client.post("/books", json={
    "title": "Algorithms", "author": "CLRS", "total_copies": 1
})
assert created.status_code == 201
url = created.headers["Location"]
assert client.get(url).json()["available_copies"] == 1
assert client.post(f"{url}/borrow").status_code == 200
assert client.post(f"{url}/borrow").status_code == 409
```

The integration tests use the real middleware, router, validation, service, domain, SQL and SQLite file. They do not mock repositories. The deliberate 500 tests inject a failure only to check error handling and rollback.

`TestClient` calls the application's ASGI interface in the same process. ASGI is the interface Uvicorn uses to invoke the web app. This makes the tests fast and repeatable without opening a TCP port. A separate manual `curl` check can exercise the actual server socket.

A pytest **fixture** prepares reusable test setup. `conftest.py` creates an app and a unique temporary database for each test. Consequently tests can run repeatedly without changing your development data or depending on another test's leftovers. `MAX_COPIES=5` in tests makes boundary checks small.

Useful commands:

```bash
python -m pytest -q                         # all 60 cases
python -m pytest -v                         # individual case names
python -m pytest -m integration -q          # 50 HTTP/database integration cases
python -m pytest -m unit -q                 # 10 domain/service/configuration cases
python -m pytest tests/test_books.py -v     # book feature only
python -m pytest tests/test_storage.py -v   # persistence, rollback and race check
python -m pytest --collect-only -q          # inspect discovered cases
```

`@pytest.mark.parametrize` runs one test function once for each supplied input. That is why the case count is larger than the number of test functions.

## 13. Test cases and expected results

The following table maps the concrete scenarios to the executable test files. Each parameterized row represents multiple cases.

| ID | Scenario | Expected result | Test |
| --- | --- | --- | --- |
| B01 | Create -> fetch -> list -> update -> fetch -> delete -> fetch | 201/200/204/404, correct body and Location, persisted changes | test_books: full_crud_lifecycle |
| B02 | Return before borrowing; borrow last copy; borrow again; return; return again | 409, 200, 409, 200, 409; availability stays valid | test_books: borrow_return_lifecycle_and_conflicts |
| B03 | Increase stock while one copy is borrowed; then reduce below borrowed count | Preserve outstanding borrow; invalid update 409 and unchanged data | test_books: update_preserves_outstanding_borrows |
| B04 | Delete a borrowed book; return it; delete | 409 then 204 | test_books: cannot_delete_borrowed_book |
| B05 | Blank/long title or author; negative/excess/string/bool/fractional count | 422 with field pointer; no inserted record (10 cases) | test_books: book_field_validation |
| B06 | Invalid stock in PUT | 422; original book unchanged | test_books: book_update_validation_does_not_change_record |
| B07 | Read/update/delete/borrow/return missing book | 404 (5 cases) | test_books: missing_book_operations |
| B08 | Zero stock and a title containing SQL syntax | Title stored literally; tables intact; borrowing 409 | test_books: zero_stock_and_sql_special_characters |
| M01 | Complete member CRUD lifecycle | Correct status/body/Location; normalized email; final 404 | test_members: full_crud_lifecycle |
| M02 | Duplicate email on create and update, including case changes | 409; original records unchanged | test_members: duplicate_email_create_and_update_are_conflicts |
| M03 | Update name while keeping own email | 200 | test_members: member_can_keep_their_own_email |
| M04 | Invalid name/email | 422 with field pointer; no inserted record (5 cases) | test_members: member_validation |
| M05 | Missing member read/update/delete | 404 (3 cases) | test_members: missing_member_operations |
| M06 | Invalid member update | 422; old data preserved | test_members: invalid_member_update_is_not_saved |
| H01 | Malformed JSON, array, null, string, empty object | Same 422 problem format (5 cases) | test_http: invalid_json_or_body_shape |
| H02 | Invalid/nonpositive resource IDs | Field-level 422 (3 cases) | test_http: invalid_path_parameter |
| H03 | Unknown route and unsupported method | Problem 404/405; Allow preserved | test_http: unknown_route_and_wrong_method |
| H04 | Incomplete PUT or attempts to set server-controlled availability | 422; original record unchanged | test_http: put_requires_full_replacement_and_rejects_server_fields |
| H05 | Supplied request ID and logs | ID propagated to success/error responses and service logs | test_http: request_id_in_success_error_and_service_logs |
| H06 | Invalid/missing request ID | New bounded, distinct IDs | test_http: invalid_request_id_is_replaced_and_generated_ids_are_distinct |
| H07 | Unexpected service exception | Generic problem 500; full exception logged once | test_http: unexpected_exception_is_logged_but_hidden |
| H08 | Swagger and OpenAPI | Accessible; expected routes/error media type documented | test_http: docs_and_openapi_are_available |
| S01 | New app instance opens same database | Books, members and borrow state persist | test_storage: records_survive_a_new_app_instance |
| S02 | Save executes UPDATE then fails | 500; transaction rollback restores original book | test_storage: failed_save_rolls_back_the_whole_transaction |
| S03 | Two app instances borrow last copy concurrently | Exactly one 200 and one 409; availability zero | test_storage: simultaneous_borrows_cannot_take_the_same_last_copy |
| U01 | Call book rules directly | Borrow/return/delete guards work without HTTP | test_domain: book_domain_rules_need_no_web_server |
| U02 | Call domain validation directly | Invalid book/member raises ValidationFailed | test_domain: domain_validation_runs_outside_pydantic |
| U03 | Failed domain replacement | Existing object unchanged | test_domain: failed_domain_replace_does_not_partially_change_object |
| U04 | Inject a small in-memory repository | Service works without FastAPI or SQLite | test_domain: service_accepts_fake_storage_without_fastapi_or_sqlite |
| U05 | Invalid environment/configuration values | Fail immediately with ValueError (6 cases) | test_domain: invalid_configuration_fails_at_startup |

## 14. Optional curl demonstration

Start `python run.py` first. These book commands assume an empty development database so the created ID is 1. On an existing database, use the ID returned by POST.

```bash
# Create: expect 201 and Location: /books/1
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: lab-demo-42' \
  -d '{"title":"Clean Architecture","author":"Robert C. Martin","total_copies":1}'

# Read and list: expect 200
curl -i http://127.0.0.1:8000/books/1
curl -i http://127.0.0.1:8000/books

# Borrow: 200, then 409 because there was only one copy
curl -i -X POST http://127.0.0.1:8000/books/1/borrow
curl -i -X POST http://127.0.0.1:8000/books/1/borrow

# Return: expect 200
curl -i -X POST http://127.0.0.1:8000/books/1/return

# Update: expect 200, same ID, total and available now 2
curl -i -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Architecture, revised","author":"Robert C. Martin","total_copies":2}'

# Delete: 204 with no body; subsequent GET: 404
curl -i -X DELETE http://127.0.0.1:8000/books/1
curl -i http://127.0.0.1:8000/books/1
```

Members have the same lifecycle:

```bash
curl -i -X POST http://127.0.0.1:8000/members \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ayesha Rahman","email":"ayesha@example.com"}'
curl -i http://127.0.0.1:8000/members
curl -i http://127.0.0.1:8000/members/1
curl -i -X PUT http://127.0.0.1:8000/members/1 \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ayesha","email":"reader@example.com"}'
curl -i -X DELETE http://127.0.0.1:8000/members/1
curl -i http://127.0.0.1:8000/members/1
```

## 15. Dependency management

`requirements.in` declares direct dependencies. `requirements.txt` locks exact versions, transitive dependencies and SHA-256 package hashes. Installing with `--require-hashes` checks the downloaded artifacts against that lock.

The application imports Pydantic and Starlette directly, so both are declared explicitly rather than relying only on FastAPI's dependencies.

To intentionally update the lock, use a separate tools environment so build/audit tools do not become application dependencies:

```bash
python3 -m venv /tmp/bookshelf-tools
/tmp/bookshelf-tools/bin/python -m pip install pip-tools pip-audit
/tmp/bookshelf-tools/bin/python -m piptools compile \
  --upgrade --generate-hashes --strip-extras --no-emit-index-url \
  --index-url https://pypi.org/simple \
  --output-file requirements.txt requirements.in
python -m pip install --require-hashes -r requirements.txt
python -m pytest -q
/tmp/bookshelf-tools/bin/python -m pip_audit --require-hashes -r requirements.txt
```

Lock generation and audits need internet access. Review the resulting changes and release notes before upgrading. Commit both dependency files; do not commit virtual environments, local databases or `.env`.

## 16. Scope and tradeoffs

This is a small backend assignment with two features. Members are a directory; inventory borrowing tracks **how many** copies are outstanding, not **which member** has each copy. There is no loans resource, due-date system, fine calculation, authentication, or authorization.

Adding member-linked lending would require a Loan domain object/repository and a service that changes the loan and book inventory in the same transaction. The existing shared-transaction structure can support that extension.

SQLite is convenient for a local lab. Its serialized writes and this project's deliberately simple transaction wrapper are less suitable for high traffic. Collection endpoints also return the full list rather than paginating it. Schema creation is automatic; versioned migrations are not implemented.

The framework helps with parsing and validation, but it cannot invent access-control rules. This unauthenticated demo should be extended with those rules before handling real library data.

## 17. Suggested viva walkthrough

1. Start at `create_app()` and identify configuration and dependency wiring.
2. Read `routes/books.py`; explain why the handler is short.
3. Follow `borrow_book()` into the service.
4. Explain `Book.borrow()` and why the rule belongs in the domain.
5. Identify the SQL in `BookRepository` and transaction handling in `Database`.
6. Run the borrow test to show the 200 -> 409 -> return behavior.
7. Run both CRUD lifecycle tests to show automated Postman-style checks.
8. Show the injected-failure test: safe 500 to the client, full exception in logs.
9. Explain why the service can also run with fake storage.
10. Explain the difference between total and available copies.

The repository link and meaningful commit history are submission steps for the student; this implementation does not create or publish a remote repository.

## 18. AI-use disclosure and verification

OpenAI Codex assisted with implementing the FastAPI backend, designing automated tests and writing this explanation. The implementation was guided by the professor's supplied slides and checked against official framework documentation.

Verification performed includes the 60 automated cases described above, installation from the hash-locked dependency file in a clean virtual environment, and real HTTP requests to a temporary Uvicorn server for both CRUD lifecycles and failure paths. OpenAPI references were also checked. The automated cases check actual state after changes and failed operations, not just response status codes.

The locked dependencies were checked with pip-audit on November 25, 2026; it reported no known vulnerabilities. This is a dated audit result, not a guarantee about future advisories.

The student should review the source, rerun the tests locally, and be able to explain the submitted code and design decisions. AI assistance does not substitute for that understanding.
