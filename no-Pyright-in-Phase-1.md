Turned out Pyright "browser bundles" is a thing of the past,
e.g. `@typefox/pyright-browser` NPM package is 2 years old.

See [2024-10-26 zsheng: Integrating LSP with the Monaco Code Editor](https://medium.com/@zsh-eng/integrating-lsp-with-the-monaco-code-editor-b054e9b5421f) for links and personal account.

*zsheng* 
* "found two incredibly helpful videos by TJ DeVries":
  * [LSP Explained in 5 minutes](https://www.youtube.com/watch?v=LaS32vctfOY)
  * [Building Language Server](https://www.youtube.com/watch?v=YsdlcQoHqPY) (mainly focused on the first 30 minutes)
* [LSP specification-3-16.md](https://github.com/microsoft/language-server-protocol/blob/gh-pages/_specifications/specification-3-16.md) or [nicely rendered](https://microsoft.github.io/language-server-protocol/specifications/specification-3-16/)
* eventually discovered Monaco Editor already includes TypeScript/JavaScript completions out of the box.
^ had to follow the LSP specification’s lifecycle precisely:
  1. Send an initialize request (together with params describing the client’s capabilities).
  2. Wait for the server to respond (do not send any other requests until the server responds).
  3. Send an initialized notification to tell the server that the client is ready.
^ had to manually sync the document content. On the client:
  1. Tell the server about new documents with textDocument/didOpen
  2. Keep it updated with textDocument/didChange
  Otherwise, the server might try to read the document using the document’s URI.
* had to switch to `pylsp` (Python Language Server), for pyright-langserver
  ^ closed after textDocument/didOpen
  ^ gave no error messages in stderr
  and *zsheng* couldn’t figure out what was going wrong.
^ suggests: Start with the Basics:
  * Read the LSP spec first for a fundamental understanding
  * Try with simple examples
  * Take time to understand how everything fits together
  Debug Smarter:
  * Follow the protocol steps exactly
  * Use the debugger to step through the process
* plans to Add collaborative editing with Yjs
