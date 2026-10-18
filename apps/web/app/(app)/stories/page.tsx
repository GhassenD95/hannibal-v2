'use client';

import * as React from 'react';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { EmptyState, ErrorState, LoadingState, Spinner } from '@/components/ui/states';
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table';
import { Tabs, TabItem, TabsPanel } from '@/components/ui/tabs';

const STATUSES = [
  'draft',
  'requested',
  'drafted',
  'supported',
  'needs_review',
  'unsupported',
  'validated',
  'approved',
  'rejected',
  'escalated',
];

export default function StoriesPage() {
  const [tab, setTab] = React.useState('buttons');
  const [text, setText] = React.useState('');
  const [area, setArea] = React.useState('');
  const [select, setSelect] = React.useState('service_agreement');

  const tabs: TabItem[] = [
    { value: 'buttons', label: 'Buttons' },
    { value: 'badges', label: 'Badges' },
    { value: 'alerts', label: 'Alerts' },
    { value: 'forms', label: 'Forms' },
    { value: 'states', label: 'States' },
    { value: 'tabs', label: 'Tabs & tables' },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted">Design system</p>
        <h1 className="mt-1 text-2xl font-semibold text-ink">Component stories</h1>
        <p className="mt-2 text-sm text-muted">
          Reference gallery of every shared component with its loading, empty, error, success,
          warning, and disabled states. Screens must reuse these components rather than invent
          one-off styles.
        </p>
      </div>

      <Tabs items={tabs} value={tab} onChange={setTab} label="Component story groups">
        <TabsPanel value="buttons">
          <section className="flex flex-col gap-4">
            <div className="flex flex-wrap items-end gap-3">
              <Button variant="primary">Primary action</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Danger</Button>
              <Button variant="link">Link button</Button>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <Button variant="primary" size="sm">
                Small
              </Button>
              <Button variant="primary" size="md">
                Default
              </Button>
              <Button variant="primary" loading loadingText="Working…">
                Loading
              </Button>
              <Button variant="primary" disabled>
                Disabled
              </Button>
              <Button variant="secondary" disabled>
                Disabled secondary
              </Button>
            </div>
            <p className="text-sm text-muted">
              One primary action per screen. Disabled controls keep their label visible so users can
              still read what is blocked.
            </p>
          </section>
        </TabsPanel>

        <TabsPanel value="badges">
          <section className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant="neutral">neutral</Badge>
              <Badge variant="info">info</Badge>
              <Badge variant="primary">primary</Badge>
              <Badge variant="success">success</Badge>
              <Badge variant="warning">warning</Badge>
              <Badge variant="danger">danger</Badge>
              <Badge variant="evidence">evidence</Badge>
            </div>
            <div className="flex flex-wrap gap-2">
              {STATUSES.map((status) => (
                <StatusBadge key={status} status={status} />
              ))}
            </div>
            <p className="text-sm text-muted">
              Status colors are always paired with a text label — never communicated by color alone.
            </p>
          </section>
        </TabsPanel>

        <TabsPanel value="alerts">
          <section className="flex flex-col gap-3">
            <Alert variant="info" title="Informational note">
              Facts are collected here; no legal drafting happens in this step.
            </Alert>
            <Alert variant="success" role="status" title="Validation passed">
              All blocker checks currently pass. Human review is still required.
            </Alert>
            <Alert variant="warning" title="Human review required">
              {3} section(s) need review before approval.
            </Alert>
            <Alert variant="danger" title="Export blocked">
              Resolve all open blockers before exporting.
            </Alert>
          </section>
        </TabsPanel>

        <TabsPanel value="forms">
          <section className="grid max-w-3xl gap-4 sm:grid-cols-2">
            <FormField
              id="story-input"
              label="Contract name"
              required
              hint="Shown on the dashboard"
            >
              <Input
                id="story-input"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Service agreement — Acme"
              />
            </FormField>
            <FormField id="story-disabled" label="Contract id" hint="Read-only value">
              <Input id="story-disabled" value="42" readOnly disabled />
            </FormField>
            <FormField
              id="story-error"
              label="Amount"
              required
              error="Enter a numeric amount greater than zero."
            >
              <Input id="story-error" defaultValue="free" />
            </FormField>
            <FormField id="story-select" label="Contract type">
              <Select
                id="story-select"
                value={select}
                onChange={(event) => setSelect(event.target.value)}
              >
                <option value="service_agreement">service_agreement</option>
                <option value="nda">nda</option>
              </Select>
            </FormField>
            <FormField id="story-area" label="Description" className="sm:col-span-2">
              <Textarea
                id="story-area"
                rows={4}
                value={area}
                onChange={(event) => setArea(event.target.value)}
                placeholder="Describe the arrangement in plain language…"
              />
            </FormField>
          </section>
        </TabsPanel>

        <TabsPanel value="states">
          <section className="grid gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Loading</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <LoadingState label="Loading contract workspace…" />
                <div className="flex items-center gap-2 text-sm text-muted">
                  <Spinner className="text-primary" /> Inline spinner
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Empty</CardTitle>
              </CardHeader>
              <CardContent>
                <EmptyState
                  title="No negotiation items"
                  description="Create an item from the counterparty wording to analyze, propose, and decide."
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Error</CardTitle>
              </CardHeader>
              <CardContent>
                <ErrorState
                  message="Cannot reach the Hannibal API. Check that the backend is running."
                  onRetry={() => undefined}
                />
              </CardContent>
            </Card>
          </section>
        </TabsPanel>

        <TabsPanel value="tabs">
          <section className="flex flex-col gap-6">
            <Tabs
              items={[
                { value: 'one', label: 'First tab' },
                {
                  value: 'two',
                  label: 'Second tab',
                  badge: <Badge variant="danger">2</Badge>,
                },
                { value: 'three', label: 'Third tab' },
              ]}
              value={tab === 'tabs' ? 'one' : 'one'}
              onChange={() => undefined}
              label="Static tab demo"
            >
              <TabsPanel value="one">
                <p className="text-sm text-muted">
                  Tabs are keyboard operable: use arrow keys, Home, and End. Panels keep focus order
                  stable.
                </p>
              </TabsPanel>
            </Tabs>

            <Table caption="Example data table">
              <THead>
                <TR>
                  <TH scope="col">Section</TH>
                  <TH scope="col">Status</TH>
                  <TH scope="col">Evidence</TH>
                </TR>
              </THead>
              <TBody>
                <TR>
                  <TD>Confidentiality</TD>
                  <TD>
                    <StatusBadge status="supported" />
                  </TD>
                  <TD>
                    <Badge variant="evidence">3 sources</Badge>
                  </TD>
                </TR>
                <TR>
                  <TD>Liability</TD>
                  <TD>
                    <StatusBadge status="needs_review" />
                  </TD>
                  <TD>
                    <Badge variant="warning">no approved source</Badge>
                  </TD>
                </TR>
              </TBody>
            </Table>
          </section>
        </TabsPanel>
      </Tabs>
    </div>
  );
}
