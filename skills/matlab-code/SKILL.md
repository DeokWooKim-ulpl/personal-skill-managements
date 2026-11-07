---
name: "matlab-code"
description: "Generates clean MATLAB scripts adhering to strict figure formatting, LaTeX axis labels, and code structuring guidelines. Use when the user invokes /matlab-code, mentions matlab-code, or asks to generate MATLAB code and plots following specific publication/figure styling rules."
---

# MATLAB Code Generation

Generate MATLAB scripts strictly following the execution and styling rules below.

## Code Structure Rules

- Do NOT use `%%` to create sections or divide code.
- Do NOT include any comments (`%` or `%{ ... %}`). The code must be completely clean and comment-free.

## Figure & Plot Styling Rules

When creating figure windows and axes:

1. **Figure Creation & Sizing**:
   ```matlab
   f1 = figure(1); % Use figure(#) pattern (e.g. f1 = figure(1); or fn = figure(n);)
   f1.Position = [0 0 1400 800];
   ```

2. **Font & Axes Defaults**:
   ```matlab
   set(gca,'FontSize',30);
   grid off;
   ax = gca;
   ax.LineWidth = 3;
   box on;
   ```

3. **Labels & Title**:
   - `xlabel('물리량 [단위]','FontSize',40,'Interpreter','latex')`
   - `ylabel('물리량 [단위]','FontSize',40,'Interpreter','latex')`
   - Do NOT include any title (`title(...)` is strictly forbidden).

4. **Dual-Axis (`yyaxis`) Rules**:
   - Unless specifically instructed otherwise, when using `yyaxis left` and `yyaxis right`, set the axis box outline to solid black:
     ```matlab
     ax = gca;
     ax.YAxis(1).Color = 'black';
     ax.YAxis(2).Color = 'black';
     ```
   - Both left and right y-labels must use `'FontSize',40,'Interpreter','latex'`.