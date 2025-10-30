import React from 'react';
import { render } from '@testing-library/react-native';
import App from '../App';

/**
 * Smoke test - ensures app renders without crashing
 */
describe('App', () => {
  it('renders without crashing', () => {
    const { getByText } = render(<App />);
    // App should render something (could be loading state or auth screen)
    expect(getByText).toBeDefined();
  });
});

