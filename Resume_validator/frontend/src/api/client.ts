import axios from 'axios';

// Override with VITE_API_BASE_URL in a .env file if the API runs elsewhere.
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({ baseURL });

export default api;
