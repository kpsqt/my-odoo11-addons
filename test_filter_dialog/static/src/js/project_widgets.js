odoo.define('web.test_filter_dialog', function (require) {
    "use strict";

    var core = require('web.core');

    var dialogs = require('web.view_dialogs');

    // var ProgressBar = require('web.ProgressBar');
    var pyeval = require('web.pyeval');
    var Registry = require('web.Registry');
    var session = require('web.session');
    var Widget = require('web.Widget');
    var data = require('web.data');
    var QWeb = core.qweb;
    var _t = core._t;
    // var Model = require('web.DataModel');
    var rpc = require('web.rpc');
    var FormView = require('web.FormView');
    var widgetRegistry = require('web.widget_registry');
    var FieldManagerMixin = require('web.FieldManagerMixin');


    var ModuleReviewListDialog = Widget.extend({
        events: {
            'hidden.bs.modal': 'destroy',
        },
        template: 'c1_project_dev.ModuleReviewListDialog',
        init: function (module_id) {
            // this._super(parent);
            // console.log(parent);
            // console.log(object);
            this.module_id = module_id;
            return this._super.apply(this, arguments);
        },
        start: function () {
            console.log(this.module_id.name);
            // this.$el.find('h3.modal-title').text(this.module_id.name);
            this.$el.modal();
        },
    });

    var ModuleRevisionMarkFormWidget = Widget.extend(FieldManagerMixin, {
        init: function (parent, object, state) {
            this._super(parent);
            FieldManagerMixin.init.call(this);
            this.data = object.data;
            this.mode = parent.mode || 'readonly';
        },
        events: {
            'click button.ct_composer_button_uprate': "up_rate",
            'click button.ct_composer_button_downrate': "down_rate",
            'click a.ct_mark_link': "display_composer",
            'click a.ct_see_all_mark_link': "display_revision_dialog",
            'click a.ct_composer_cancel_link': "hide_composer",
        },
        start: function () {
            if (this.data.module_id == false) {
                return;
            }
            console.log(this.data.module_id.data.id);
            var self = this;
            if (self.mode == 'readonly') {
                this._rpc({
                    model: 'c1_project_dev.module.review',
                    method: 'get_last_review',
                    args: [this.data.module_id.data.id],
                }).then(function (last_review) {
                    // console.log(last_review);
                    self.display_widget(last_review);
                });
            }

        },
        display_widget: function (last_review) {
            this.$el.html(QWeb.render("ModuleRevisionMarkFormWidget", {
                'reviews': last_review, // 'avatar_url': '/web/image/res.partner/' + last_review.user.partner_id + '/image_small',
            }));
            this.$('.ct_composer_container').hide();
        },
        up_rate: function () {
            var self = this;
            var comment = self.$('.o_composer_text_field').val();
            this._rpc({
                model: 'c1_project_dev.module.review',
                method: 'rate',
                args: [this.data.module_id.data.id, this.data.current_downloaded_rev, 'good', comment],
            }).then(function (res) {
                if (_.isEmpty(res)) {
                    // self.$('.o_hr_attendance_employee').append(_t("Error : Could not find employee linked to user"));
                    return;
                }
                // console.log(res);
                self.$('.o_composer_text_field').val('');
                self.$('.ct_composer_container').slideUp();
                self.restart();
            });
        },
        down_rate: function () {
            var self = this;
            var comment = self.$('.o_composer_text_field').val();
            this._rpc({
                model: 'c1_project_dev.module.review',
                method: 'rate',
                args: [this.data.module_id.data.id, this.data.current_downloaded_rev, 'not_good', comment],
            }).then(function (res) {
                if (_.isEmpty(res)) {
                    return;
                }
                // console.log(res);
                self.$('.o_composer_text_field').val('');
                self.$('.ct_composer_container').slideUp();
                self.restart();
            });
        },
        display_composer: function () {
            var self = this;
            // console.log(this.data.current_downloaded_rev);
            self.$('.ct_composer_container').slideDown();
            self.$('.o_composer_text_field').attr('placeholder', 'Comment revision ' + this.data.current_downloaded_rev);
        },
        hide_composer: function () {
            var self = this;
            self.$('.o_composer_text_field').val('');
            self.$('.ct_composer_container').slideUp();
        },
        restart: function () {
            var self = this;
            self.$el.empty();
            self.start();
        },
        display_revision_dialog: function () {
            var dialog = new ModuleReviewListDialog(this.data.module_id);
            var self = this;
            this._rpc({
                model: 'c1_project_dev.module.review',
                method: 'get_reviews',
                args: [self.data.module_id.data.id],
            }).then(function (res) {
                dialog.$el.find('.o_mail_thread').empty().append(QWeb.render('review_list', {
                    'reviews': res,
                }));
                dialog.$el.find('.modal-title').empty().append(self.data.module_id.data.display_name + '');
            });
            dialog.appendTo($(document.body));
        }
    });

    /*core.form_custom_registry.add(
     'module_revision_marker', ModuleRevisionMarkFormWidget
     );*/
    widgetRegistry.add('module_revision_marker', ModuleRevisionMarkFormWidget);


    // var ModulesFilter = form_common.FormWidget.extend({
    var ModulesFilter = Widget.extend(FieldManagerMixin, {
        // template: "RemoteDatabaseModuleFilter",
        init: function (parent, object) {
            this._super(parent);
            FieldManagerMixin.init.call(this);
            // console.log('INIT!!!');
            // console.log(object);
            this.data = object.data;

            // this._super.apply(this, arguments);
        },
        start: function () {
            this.display_filter();
        },
        events: {
            "click .ct_button_filter": "open_search_dialog",
        },
        open_search_dialog: function () {
            var self = this;
            console.log(self.data.id);
            new dialogs.SelectCreateDialog(this, _.extend({}, (this.options || {}), {
                res_model: 'c1_project_dev.module.info',
                domain: [['database_id', '=', self.data.id]],
                context: {},
                title: _t("Search modules in ") + self.data.name,
                disable_multiple_selection: true,
                on_selected: function (element_ids) {
                    console.log(element_ids);
                },
                no_create: true
            })).open();
        },
        display_filter: function () {
            this.$el.html(QWeb.render("RemoteDatabaseModuleFilter", {}));
        },
    });

    core.form_custom_registry.add(
        'remote_db_module_filter', ModulesFilter
    );

    widgetRegistry.add('remote_db_module_filter', ModulesFilter);


    var SearchImport = dialogs.SelectCreateDialog.extend({
        init: function (parent, options) {
            options = options || {};
            options.dialogClass = options.dialogClass || '' + ' o_act_window';

            this._super(parent, $.extend(true, {}, options));

            this.res_model = 'project.task';
            // this.domain = options.domain || [];
            // this.context = options.context || {};
            this.options = _.extend(this.options || {}, options || {});
            this.no_create = true;

            this.dataset = new data.DataSet(this, this.res_model, this.context);

            this.on_selected = function (item_ids) {
                var self = this;
                /*this._rpc({
                    model: 'model_name',
                    method: 'method_name',
                    args: item_ids,
                }).then(function (res) {
                    self.close();
                });*/
                this.close();
            }

            this.open();
        }
    });

    core.action_registry.add(
        'test_filter_dialog.search_import', SearchImport
    );

});