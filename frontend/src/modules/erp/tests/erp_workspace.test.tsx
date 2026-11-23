import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UploadZone } from '../components/UploadZone';
import { KPICards } from '../components/KPICards';
import { VerificationPanel } from '../components/VerificationPanel';

describe('ERP Import Workspace Frontend Component Suite', () => {
  it('renders UploadZone drop area', () => {
    render(<UploadZone />);
    expect(screen.getByText(/Upload ERP Workbook/i)).toBeInTheDocument();
    expect(screen.getByText(/Drag & drop your Excel or CSV file here/i)).toBeInTheDocument();
  });

  it('renders KPICards with default metrics', () => {
    render(<KPICards />);
    expect(screen.getByText(/Total Imports/i)).toBeInTheDocument();
    expect(screen.getByText(/Data Confidence/i)).toBeInTheDocument();
    expect(screen.getByText(/100%/i)).toBeInTheDocument();
  });

  it('renders VerificationPanel checks', () => {
    render(<VerificationPanel />);
    expect(screen.getByText(/Backend Integrity & Verification Panel/i)).toBeInTheDocument();
    expect(screen.getByText(/Workbook File Stored in Local Storage Provider/i)).toBeInTheDocument();
  });
});
