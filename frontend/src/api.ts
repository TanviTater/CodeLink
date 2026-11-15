import axios from 'axios'
export const api=axios.create({baseURL:import.meta.env.VITE_API_URL||'http://localhost:8000/api'})
export const getProjects=()=>api.get('/projects').then(r=>r.data)
export const createProject=(name:string,topology:any)=>api.post('/projects',{name,topology}).then(r=>r.data)
export const updateProject=(id:number,payload:any)=>api.put(`/projects/${id}`,payload).then(r=>r.data)
export const simulate=(id:number,params:any)=>api.post(`/projects/${id}/simulate`,params).then(r=>r.data)
export const getRuns=()=>api.get('/runs').then(r=>r.data)
export const getAnalytics=()=>api.get('/analytics').then(r=>r.data)
