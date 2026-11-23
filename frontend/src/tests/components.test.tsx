import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  AppCard,
  CardHeader,
  CardBody,
  CardFooter,
  Button,
  TextInput,
  Select,
  StatusChip,
  DataTable,
  Modal,
} from '../components';

describe('Shared UI Framework Component Library', () => {
  it('renders AppCard container with header, body and footer', () => {
    render(
      <AppCard>
        <CardHeader title="Test Card" subtitle="Test Subtitle" />
        <CardBody>Card Body Content</CardBody>
        <CardFooter>Card Footer Content</CardFooter>
      </AppCard>
    );

    expect(screen.getByText('Test Card')).toBeInTheDocument();
    expect(screen.getByText('Test Subtitle')).toBeInTheDocument();
    expect(screen.getByText('Card Body Content')).toBeInTheDocument();
    expect(screen.getByText('Card Footer Content')).toBeInTheDocument();
  });

  it('renders Button with variants and handles click events', () => {
    const handleClick = vi.fn();
    render(
      <Button variant="primary" onClick={handleClick}>
        Click Me
      </Button>
    );

    const btn = screen.getByText('Click Me');
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders TextInput and handles change events', () => {
    const handleChange = vi.fn();
    render(<TextInput label="Username" onChange={handleChange} placeholder="Enter username" />);

    const input = screen.getByPlaceholderText('Enter username');
    fireEvent.change(input, { target: { value: 'operator1' } });
    expect(handleChange).toHaveBeenCalled();
  });

  it('renders Select dropdown with options', () => {
    render(
      <Select
        label="Environment"
        options={[
          { label: 'Production', value: 'prod' },
          { label: 'Staging', value: 'stage' },
        ]}
      />
    );

    expect(screen.getByText('Environment')).toBeInTheDocument();
    expect(screen.getByText('Production')).toBeInTheDocument();
  });

  it('renders StatusChip with status colors', () => {
    render(<StatusChip label="HEALTHY" status="success" />);
    expect(screen.getByText('HEALTHY')).toBeInTheDocument();
  });

  it('renders DataTable with columns and generic data', () => {
    const columns = [
      { header: 'ID', accessorKey: 'id' as const },
      { header: 'Name', accessorKey: 'name' as const },
    ];
    const data = [
      { id: '1', name: 'Node A' },
      { id: '2', name: 'Node B' },
    ];

    render(<DataTable columns={columns} data={data} />);
    expect(screen.getByText('Node A')).toBeInTheDocument();
    expect(screen.getByText('Node B')).toBeInTheDocument();
  });

  it('renders Modal dialog when open and triggers onClose', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Operational Confirmation">
        <div>Are you sure?</div>
      </Modal>
    );

    expect(screen.getByText('Operational Confirmation')).toBeInTheDocument();
    fireEvent.click(screen.getByText('✕'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
