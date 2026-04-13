import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders main recipe predictor heading', () => {
  render(<App />);
  const title = screen.getByText(/predict the recipe from your ingredients/i);
  expect(title).toBeInTheDocument();
});

test('renders auth and articles tabs', () => {
  render(<App />);
  expect(screen.getByRole('tab', { name: /auth/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /articles/i })).toBeInTheDocument();
});
