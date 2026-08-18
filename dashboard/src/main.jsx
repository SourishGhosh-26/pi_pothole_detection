import React from 'react'
import ReactDOM from 'react-dom/client'
import 'leaflet/dist/leaflet.css' // CRITICAL Leaflet CSS import to prevent blank black box bug
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
