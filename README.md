# Adviseur

**AI-powered client communication triage and workflow assistant for financial advisors.**

Adviseur is a Python-based application designed to help financial advisory practices manage incoming client communication, identify urgent requests, maintain client records, and route messages through an AI-assisted triage workflow.

> **Project status:** Active development / prototype

---

## The Problem

Financial advisors can receive large volumes of client communication involving:

- investment queries
- document requests
- administrative requests
- portfolio concerns
- urgent financial matters
- general client support

When an advisor is unavailable, these messages still need to be identified, prioritised and routed appropriately.

Adviseur explores how AI can assist with this workflow while keeping human oversight for sensitive or high-priority cases.

---

## Core Workflow

```text
Client Message
      ↓
Adviseur
      ↓
AI Classification
      ↓
Category + Urgency + Reason
      ↓
Recommended Action
      ↓
Human Review Required?
      ↓
PostgreSQL
      ↓
Advisor Dashboard