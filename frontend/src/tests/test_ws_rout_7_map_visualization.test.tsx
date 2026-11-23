import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RouteMapVisualization } from '../modules/operational_dashboard/components/RouteAnalysis/RouteMapVisualization';
import { RouteAnalysisSynthesisResult } from '../modules/operational_dashboard/components/RouteAnalysis/routeAnalysis.types';

describe('WS-ROUT-7: Google Map Visualization & Decision Support Tests', () => {
  const mockDetailedRouteResult: RouteAnalysisSynthesisResult = {
    analysis_id: 'snap-map-001',
    dispatch_id: 'disp-map-001',
    dispatch_number: 'DSP-MAP-2026-001',
    trip_number: 'TRIP-MAP-001',
    site_id: 'site-map-1',
    site_code: 'SITE_DHARGAL_TOWER',
    site_name: 'Dhargal Tower Delivery Site',
    site_latitude: 15.5630,
    site_longitude: 73.7660,
    current_source_plant_id: 'plant-vasco-id',
    current_source_plant_code: 'ACC_VASCO',
    current_source_plant_name: 'ACC VASCO Plant',
    current_source_plant_latitude: 15.3991,
    current_source_plant_longitude: 73.8153,
    recommended_plant_id: 'plant-kundaim-id',
    recommended_plant_code: 'ACC_KUNDAIM',
    recommended_plant_name: 'ACC KUNDAIM Plant',
    recommendation_status: 'RECOMMEND_ALTERNATIVE',
    primary_case_category: 'C2_BOTH_AGREE_ALTERNATIVE',
    is_traffic_override: false,
    decision_reason_summary: 'Plant ACC_KUNDAIM is recommended: saves 15.0 mins in live Google traffic.',
    minutes_saved: 15.0,
    engine_version: 'v1.2.1',
    policy_version: 'ROUTE_POLICY_v1.2.1',
    analysis_mode: 'NOW',
    requested_departure_time: null,
    analysis_timestamp: '2026-09-09T04:00:00Z',
    is_google_fresh: true,
    is_google_stale_cache: false,
    google_cache_age_seconds: 40,
    is_historical_sufficient: true,
    detailed_route: {
      plant_id: 'plant-kundaim-id',
      plant_code: 'ACC_KUNDAIM',
      site_id: 'site-map-1',
      site_code: 'SITE_DHARGAL_TOWER',
      encoded_polyline: 'ms~|Au`paMVIaAmCk@aBOUd@u@rAaBFYq@}HMiAu@mIOaA_@yEw@aHGaB',
      duration_seconds: 2100,
      duration_minutes: 35.0,
      static_duration_seconds: 1800,
      static_duration_minutes: 30.0,
      traffic_delay_minutes: 5.0,
      distance_meters: 28500,
      distance_km: 28.5,
      speed_reading_intervals: [
        {
          start_polyline_point_index: 0,
          end_polyline_point_index: 5,
          speed_state: 'NORMAL',
          color_hex: '#10B981',
        },
        {
          start_polyline_point_index: 5,
          end_polyline_point_index: 10,
          speed_state: 'SLOW',
          color_hex: '#F59E0B',
        },
      ],
    },
    google_evidence: {
      provider: 'GOOGLE_ROUTES_V2',
      detailed_routes: {
        'plant-vasco-id': {
          plant_id: 'plant-vasco-id',
          plant_code: 'ACC_VASCO',
          site_id: 'site-map-1',
          site_code: 'SITE_DHARGAL_TOWER',
          encoded_polyline: 'ms~|Au`paMVIaAmCk@aBOUd@u@rAaBFYq@}HMiAu@mIOaA_@yEw@aHGaB',
          duration_seconds: 3000,
          duration_minutes: 50.0,
          distance_meters: 39800,
          distance_km: 39.8,
        },
        'plant-kundaim-id': {
          plant_id: 'plant-kundaim-id',
          plant_code: 'ACC_KUNDAIM',
          site_id: 'site-map-1',
          site_code: 'SITE_DHARGAL_TOWER',
          encoded_polyline: 'ms~|Au`paMVIaAmCk@aBOUd@u@rAaBFYq@}HMiAu@mIOaA_@yEw@aHGaB',
          duration_seconds: 2100,
          duration_minutes: 35.0,
          distance_meters: 28500,
          distance_km: 28.5,
        },
      },
    },
    comparisons: [
      {
        candidate_plant_id: 'plant-kundaim-id',
        candidate_plant_code: 'ACC_KUNDAIM',
        candidate_plant_name: 'ACC KUNDAIM Plant',
        google_candidate_distance_km: 28.5,
        google_candidate_duration_minutes: 35.0,
      },
    ],
    historical_evidence: null,
  };

  it('renders Google Map container with corridor header and live traffic badge', () => {
    render(<RouteMapVisualization result={mockDetailedRouteResult} />);

    expect(screen.getByTestId('route-map-container')).toBeInTheDocument();
    expect(screen.getByText('Physical Corridor Route Visualization')).toBeInTheDocument();
    expect(screen.getByText('Live Google Traffic')).toBeInTheDocument();
    expect(screen.getByText(/Approved Plant \(ACC_VASCO\) → Destination Site \(SITE_DHARGAL_TOWER\)/i)).toBeInTheDocument();
  });

  it('renders candidate route badges allowing operator selection synchronization', () => {
    const handleSelect = vi.fn();
    render(
      <RouteMapVisualization
        result={mockDetailedRouteResult}
        selectedCandidateId="plant-kundaim-id"
        onSelectCandidate={handleSelect}
      />
    );

    const vascoBtns = screen.getAllByText('ACC_VASCO');
    const kundaimBtns = screen.getAllByText('ACC_KUNDAIM');

    expect(vascoBtns.length).toBeGreaterThan(0);
    expect(kundaimBtns.length).toBeGreaterThan(0);

    fireEvent.click(vascoBtns[0]);
    expect(handleSelect).toHaveBeenCalledWith('plant-vasco-id');
  });

  it('renders deterministic missing coordinates warning without fabricating route when coordinates are null', () => {
    const missingCoordsResult: RouteAnalysisSynthesisResult = {
      ...mockDetailedRouteResult,
      site_latitude: null,
      site_longitude: null,
      recommendation_status: 'LOCATION_DATA_MISSING',
      primary_case_category: 'C11_COORDINATES_MISSING',
    };

    render(<RouteMapVisualization result={missingCoordsResult} />);

    expect(screen.getByTestId('route-map-missing-coords')).toBeInTheDocument();
    expect(screen.getByText(/Route Visualization Unavailable — Coordinates Missing/i)).toBeInTheDocument();
    expect(screen.queryByTestId('route-map-container')).not.toBeInTheDocument();
  });

  it('renders unavailable placeholder when polyline evidence is missing', () => {
    const noPolylineResult: RouteAnalysisSynthesisResult = {
      ...mockDetailedRouteResult,
      detailed_route: null,
      google_evidence: null,
    };

    render(<RouteMapVisualization result={noPolylineResult} />);

    expect(screen.getByTestId('route-map-unavailable')).toBeInTheDocument();
    expect(screen.getByText(/Route Polyline Unavailable/i)).toBeInTheDocument();
  });

  it('renders traffic speed legend with real provider classifications (Normal, Slow, Congestion)', () => {
    render(<RouteMapVisualization result={mockDetailedRouteResult} />);

    expect(screen.getByText('Normal Traffic')).toBeInTheDocument();
    expect(screen.getByText('Slow')).toBeInTheDocument();
    expect(screen.getByText('Heavy Congestion')).toBeInTheDocument();
  });
});
