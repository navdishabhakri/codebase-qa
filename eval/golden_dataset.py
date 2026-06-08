data = [
    {
        "question": "What underlying libraries provide the foundational asynchronous routing and data validation capabilities in FastAPI?",
        "ground_truth": "FastAPI extends Starlette for ASGI routing and integrates Pydantic for data validation."
    },
    {
        "question": "How does FastAPI internally handle synchronous path functions (`def`) versus asynchronous ones (`async def`)?",
        "ground_truth": "Async functions are awaited directly on the main ASGI event loop, while synchronous functions are executed in an external thread pool via Starlette's `run_in_threadpool` to prevent blocking."
    },
    {
        "question": "What is the mechanical role of the `APIRouter` class in structuring large FastAPI codebases?",
        "ground_truth": "`APIRouter` serves as a modular mini-application to group related path operations independently, which are then dynamically appended to the main application via `app.include_router()`."
    },
    {
        "question": "How are HTTP exception responses constructed using FastAPI's built-in `HTTPException` class?",
        "ground_truth": "It inherits from Starlette's exception model but adds deeper OpenAPI integration, accepting a `status_code` and a `detail` parameter to yield a uniform JSON payload."
    },
    {
        "question": "How can you exclude an API endpoint from appearing in the automatically generated Swagger UI/ReDoc documentation?",
        "ground_truth": "By setting the parameter `include_in_schema=False` inside the path operation decorator."
    },
    {
        "question": "How does FastAPI distinguish whether a function argument should be parsed as a Path parameter or a Query parameter?",
        "ground_truth": "Arguments matching placeholders in the route path string are parsed as Path parameters; scalar arguments not found in the path string are automatically parsed as Query parameters."
    },
    {
        "question": "What strategy does FastAPI use to capture complex, nested JSON request bodies into typed objects?",
        "ground_truth": "It relies on Pydantic `BaseModel` classes, evaluating incoming JSON request bodies against the model schema to provide fully validated Python objects to the route."
    },
    {
        "question": "How can a developer mark an incoming query parameter as strictly mandatory or completely optional?",
        "ground_truth": "A parameter is optional if assigned a default value or typed with a `None` union (e.g., `str | None = None`). If it has no default value and isn't optional, it is strictly mandatory."
    },
    {
        "question": "What happens behind the scenes when a client sends invalid data types (e.g., passing a string text to an `int` parameter)?",
        "ground_truth": "FastAPI catches Pydantic's `ValidationError`, translates it into a `RequestValidationError`, and intercepts it with a default exception handler that returns an HTTP 422 Unprocessable Entity status with error details."
    },
    {
        "question": "How can a route function accept incoming data from an HTML form submission (`application/x-www-form-urlencoded`) instead of JSON?",
        "ground_truth": "By explicitly annotating function arguments using the `Form` parameter class (e.g., `Annotated[str, Form()]`), which overrides default JSON body processing."
    },
    {
        "question": "What is the core design philosophy behind FastAPI’s `Depends()` function?",
        "ground_truth": "It implements Dependency Injection by accepting a callable, resolving its hierarchical dependencies, executing them in order, and injecting the final output directly into the route function arguments."
    },
    {
        "question": "How does FastAPI’s dependency caching work across a single incoming HTTP request?",
        "ground_truth": "By default, if the same dependency is called multiple times within a single request, FastAPI reuses the cached output from the first execution unless overridden with `use_cache=False`."
    },
    {
        "question": "How do you gracefully initialize and safely tear down resources (like database sessions) using dependencies?",
        "ground_truth": "By writing a generator dependency using Python’s `yield` statement; setup code runs before the endpoint executes, and cleanup code runs after the endpoint completes."
    },
    {
        "question": "How does FastAPI handle an exception that is raised inside the endpoint when using a `yield` dependency?",
        "ground_truth": "The exception is propagated back up to the generator dependency, allowing teardown logic wrapped in a `try...finally` block to catch the exception or complete cleanup actions."
    },
    {
        "question": "How can a developer apply a security dependency globally across all endpoints without declaring it inside every function signature?",
        "ground_truth": "By assigning the dependency to the global application or router instance via the `dependencies` parameter, such as `app = FastAPI(dependencies=[Depends(verify_token)])`."
    },
    {
        "question": "What is the purpose of the `lifespan` parameter in the `FastAPI` application class, and what did it replace?",
        "ground_truth": "It takes an async context manager handling application startup and shutdown lifecycle logic, replacing the deprecated `@app.on_event('startup')` and `@app.on_event('shutdown')` hooks."
    },
    {
        "question": "How does Cross-Origin Resource Sharing (CORS) security get enforced within a FastAPI repository setup?",
        "ground_truth": "It is implemented via Starlette's `CORSMiddleware`, which handles preflight `OPTIONS` requests and appends the specified allowed origins, headers, and methods to outgoing responses."
    },
    {
        "question": "What distinguishes the usage of `Security()` from standard `Depends()` when designing authentication layers?",
        "ground_truth": "While structurally identical to `Depends()`, `Security()` accepts an additional `scopes` parameter for OAuth2, mapping scope requirements directly into the generated OpenAPI documentation."
    },
    {
        "question": "How can you return a completely raw, unformatted custom string response from an endpoint instead of automated JSON?",
        "ground_truth": "By configuring the `response_class` parameter in the decorator or explicitly returning a raw Starlette response class like `PlainTextResponse` or `HTMLResponse`."
    },
    {
        "question": "How can a test suite dynamically mock or substitute database sessions or third-party API dependencies without refactoring the application code?",
        "ground_truth": "By utilizing the `app.dependency_overrides` dictionary to map original dependency callables to mocked replacements for the duration of the test execution."
    }
]