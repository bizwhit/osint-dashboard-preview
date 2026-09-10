import type { Config } from 'tailwindcss';
const config: Config = {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: { colors: { ink: '#07111f', panel: '#0d1b2a', line: '#1d3248', cyan: '#28d7f0', lime: '#9fea42', amber: '#ffbd4a' } } },
  plugins: [],
};
export default config;
