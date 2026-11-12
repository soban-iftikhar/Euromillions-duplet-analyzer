// Use local backend when running on localhost, otherwise use the deployed Render URL
const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
  ? "http://localhost:8000" 
  : "https://euromillions-duplet-analyzer.onrender.com";
