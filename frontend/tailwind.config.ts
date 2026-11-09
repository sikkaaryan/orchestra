import type { Config } from 'tailwindcss';
const config: Config = { content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'], theme: { extend: { colors: { void: '#070710', panel: '#10101c', violet: '#9b5cff' }, boxShadow: { glow: '0 0 32px rgba(155,92,255,.18)' } } }, plugins: [] };
export default config;
