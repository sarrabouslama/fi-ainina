import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

// TODO: import pages once created
// import technicianDashboard from './pages/technicianDashboard'
// import UserDashboard from './pages/UserDashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/technician" />} />
        {/* TODO P3 frontend: add routes */}
        {/* <Route path="/technician" element={<technicianDashboard />} /> */}
        {/* <Route path="/user" element={<UserDashboard />} /> */}
        <Route path="*" element={<div style={{padding:32}}>ElderCare AI — Frontend placeholder</div>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
