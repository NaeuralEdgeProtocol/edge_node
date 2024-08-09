// Import the Express module
const express = require('express');

// Import the Morgan module
const morgan = require('morgan');

// Create an Express application
const app = express();

// Use Morgan for logging requests
app.use(morgan('dev'));

// Define a route for the root URL that sends "Hello World"
app.get('/', (req, res) => {
  res.send('Hello World');
});

// Start the server on the specified port or 3000 if not specified
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});